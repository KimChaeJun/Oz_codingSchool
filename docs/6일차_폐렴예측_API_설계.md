# 6일차 폐렴 예측 API 설계

## 1. 설계 개요

진료기록에 이미 저장된 흉부 X-Ray 이미지를 메모리에 상주한 PyTorch
ResNet18 모델로 분석하고, 결과를 `ai_analysis_results`에 저장한다.
동일한 진료기록과 동일한 모델 버전으로 생성된 결과가 있으면 모델 추론을
다시 실행하지 않고 기존 결과를 반환한다.

> 이 API의 출력은 교육용 AI 분석 결과이며 의료진의 진단을 대체하지 않는다.

## 2. 요구사항 매핑

| 요구사항 ID | 구현 항목 | API |
| --- | --- | --- |
| REQ-PRED-001 | 저장된 X-Ray를 이용한 예측 실행 및 결과 캐시 | `POST /api/v1/medical-records/{record_id}/predictions` |
| REQ-PRED-002 | 진료기록의 예측 결과 목록 조회 | `GET /api/v1/medical-records/{record_id}/predictions` |
| NFR-PRED-001 | Recall·Accuracy 기준과 모델 버전·임계값 추적 | 응답의 `model`, 모델 메타데이터 |
| NFR-PRED-002 | 모델 사전 로드, 비동기 threadpool 추론, 저장 결과 재사용 | 두 API 공통 |

## 3. 인증 및 권한

- 인증 방식: `Authorization: Bearer {access_token}`
- 허용 대상: 승인된 사내 의료인, 개발팀, 연구자 및 관리자
  - `Role.STAFF` 또는 `Role.ADMIN`
  - 가입 승인 전 `Role.PENDING` 사용자는 접근할 수 없다.
- 인증 실패: `401 Unauthorized`
- 권한 부족 또는 비활성 사용자: `403 Forbidden`

## 4. 모델 사양

| 항목 | 값 |
| --- | --- |
| 모델 버전 | `resnet18_imagenet_layer4_v1` |
| 체크포인트 | `worker/models/pneumonia_resnet18_v1.pt` |
| 입력 | 흑백 이미지를 3채널로 변환, 160×160 resize |
| 정규화 | ImageNet mean `[0.485, 0.456, 0.406]`, std `[0.229, 0.224, 0.225]` |
| 출력 클래스 | `NORMAL(0)`, `PNEUMONIA(1)` |
| 폐렴 판정 임계값 | `0.8183` |
| 검증 Recall | `0.9124` |
| 검증 Accuracy | `0.9349` |

검증 Recall과 Accuracy는 각각 NFR-PRED-001의 최소 기준 0.90, 0.80을
충족한다. 다만 이는 학습 프로젝트의 validation split 기준이며 외부 병원
데이터나 실제 임상 환경의 성능을 보장하지 않는다.

## 5. 공통 응답 필드

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `id` | integer | Y | 예측 결과 고유 ID |
| `record_id` | integer | Y | 진료기록 ID |
| `is_pneumonia` | boolean | Y | 폐렴 판정 여부 |
| `confidence` | number | Y | 반환한 판정 클래스의 신뢰도, 0~100(%) |
| `heatmap_url` | string/null | Y | Grad-CAM 등 히트맵 URL. 미생성 시 `null` |
| `predicted_at` | datetime | Y | 예측 결과 생성 시각 |
| `model` | string | Y | 추론에 사용한 모델 버전 |

`confidence`는 폐렴 판정이면 폐렴 클래스 확률, 정상 판정이면 정상 클래스
확률을 백분율로 나타낸다. 임상적으로 보정된 질병 발생 확률을 의미하지 않는다.

## 6. 폐렴 예측 실행 API

### 6.1 기본 정보

| 항목 | 내용 |
| --- | --- |
| 요구사항 ID | REQ-PRED-001 |
| Method | `POST` |
| Endpoint | `/api/v1/medical-records/{record_id}/predictions` |
| 인증 | 필수 |
| Request Body | 없음 |

클라이언트가 이미지를 다시 업로드하지 않는다. 진료기록 등록 API에서 로컬
저장소에 저장한 X-Ray 이미지 중 첫 번째 이미지를 사용한다.

### 6.2 Path Parameter

| 이름 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| `record_id` | integer | 1 이상 | 예측할 진료기록 ID |

### 6.3 처리 순서

1. access token과 사내 사용자 권한을 확인한다.
2. 진료기록과 연결된 X-Ray 이미지 존재 여부를 확인한다.
3. `(record_id, model)`이 같은 기존 결과를 조회한다.
4. 기존 결과가 있으면 추론 없이 반환하고 `cached=true`로 표시한다.
5. 기존 결과가 없으면 threadpool에서 모델 추론을 실행한다.
6. 결과를 `ai_analysis_results`에 저장한 후 반환한다.

### 6.4 성공 응답

새 결과 생성: `201 Created`

기존 결과 재사용: `200 OK`

```json
{
  "id": 11,
  "record_id": 42,
  "is_pneumonia": true,
  "confidence": 94.27,
  "heatmap_url": null,
  "predicted_at": "2026-08-31T16:30:00",
  "model": "resnet18_imagenet_layer4_v1",
  "cached": false
}
```

### 6.5 오류 응답

| 상태 | 발생 조건 |
| --- | --- |
| `401 Unauthorized` | access token이 없거나 유효하지 않음 |
| `403 Forbidden` | 미승인·비활성 사용자 또는 권한 부족 |
| `404 Not Found` | 진료기록이 존재하지 않음 |
| `409 Conflict` | 진료기록에 X-Ray 이미지가 없음 |
| `422 Unprocessable Entity` | 저장된 파일이 유효한 이미지가 아님 |
| `500 Internal Server Error` | 결과 저장 중 예상하지 못한 오류 발생 |

## 7. 폐렴 예측 결과 목록 API

### 7.1 기본 정보

| 항목 | 내용 |
| --- | --- |
| 요구사항 ID | REQ-PRED-002 |
| Method | `GET` |
| Endpoint | `/api/v1/medical-records/{record_id}/predictions` |
| 인증 | 필수 |

### 7.2 성공 응답

`200 OK`

예측 결과가 없으면 빈 배열 `[]`을 반환한다.

```json
[
  {
    "id": 11,
    "record_id": 42,
    "is_pneumonia": true,
    "confidence": 94.27,
    "heatmap_url": null,
    "predicted_at": "2026-08-31T16:30:00",
    "model": "resnet18_imagenet_layer4_v1"
  }
]
```

### 7.3 오류 응답

| 상태 | 발생 조건 |
| --- | --- |
| `401 Unauthorized` | access token이 없거나 유효하지 않음 |
| `403 Forbidden` | 미승인·비활성 사용자 또는 권한 부족 |
| `404 Not Found` | 진료기록이 존재하지 않음 |

## 8. 데이터 저장 및 중복 방지

- 테이블: `ai_analysis_results`
- 동일 결과 판단 키: `record_id + ai_model`
- 새 모델을 배포할 때 `MODEL_VERSION`을 변경하면 같은 진료기록도 새 모델로
  다시 분석할 수 있다.
- API 서비스는 추론 전에 기존 결과를 먼저 조회하여 불필요한 연산을 막는다.
- 다중 worker 환경의 경쟁 조건을 막기 위해 DB에
  `UNIQUE(record_id, ai_model)` 제약을 적용한다.
- `heatmap_url`은 선택 필드다. 이번 범위에서는 히트맵을 생성하지 않아
  DB에는 빈 문자열로 저장하고 API에서는 `null`로 변환한다.

## 9. 성능 설계

- 애플리케이션 import 시 모델을 한 번만 메모리에 로드하고 `eval()` 상태로
  유지한다.
- 요청마다 체크포인트를 다시 읽지 않는다.
- CPU/GPU 추론은 FastAPI event loop를 막지 않도록 threadpool에서 실행한다.
- 동일 모델의 저장 결과는 DB에서 즉시 반환한다.
- 파일은 진료기록 등록 단계에서 최대 10MB로 제한한다.
- 3초 기준은 모델 로딩이 끝난 정상 서비스 상태의 API 요청 시간에 적용한다.

## 10. 참고자료

- [PyTorch 모델 저장하기 & 불러오기](https://tutorials.pytorch.kr/beginner/saving_loading_models.html)
- [Torchvision ResNet18](https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.resnet18.html)
- [Torchvision Transforms](https://docs.pytorch.org/vision/stable/transforms.html)
