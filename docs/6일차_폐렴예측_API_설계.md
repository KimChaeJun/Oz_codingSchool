# 6일차 폐렴 예측 API 설계

## 1. 설계 개요

5일차까지 구축된 환자/진료기록/X-Ray 구조 위에, 진료기록에 저장된 흉부
X-Ray 이미지를 AI 모델(ResNet18)로 분석해 폐렴 여부를 예측하는 API를
설계한다. 대상 요구사항은 REQ-PRED-001, REQ-PRED-002, NFR-PRED-001,
NFR-PRED-002이다.

이번 문서는 **설계만** 다룬다. API 코드, Alembic migration은 이 문서
범위에 포함하지 않는다.

> 이 API의 출력은 학습용 프로젝트에서 검증한 AI 분석 결과이며, 의료진의
> 진단을 대체하지 않는다.

---

## 2. 요구사항 매핑

| 요구사항 ID | 내용 | 설계 반영 |
| --- | --- | --- |
| REQ-PRED-001 | 저장된 X-Ray로 예측 실행, 기존 결과 있으면 재추론 없이 반환 | `POST /api/v1/medical-records/{record_id}/predictions` |
| REQ-PRED-002 | 진료기록의 예측 결과 목록 조회 | `GET /api/v1/medical-records/{record_id}/predictions` |
| NFR-PRED-001 | Recall ≥ 0.90, Accuracy ≥ 0.80 | 3장에서 검증 수치로 근거 제시 |
| NFR-PRED-002 | 모든 API 3초 이내 응답 | 9장 성능 설계 |

---

## 3. 사용 AI 모델

### 3.1 모델 구조

- 기반: torchvision `resnet18`, ImageNet 사전학습 가중치로 초기화 후
  데이콘 해커톤 데이터로 파인튜닝
- 마지막 레이어: `model.fc`를 `nn.Linear(512, 1)`로 교체 (이진분류, 로짓 1개 출력)
- 체크포인트 형식: 전체 모델이 아닌 **state_dict만 저장** (`best_model_resnet18_pure.pth`).
  따라서 서비스 코드에서는 위 아키텍처를 먼저 재구성한 뒤
  `load_state_dict()`로 가중치를 얹어야 한다.
- 구현 위치: `worker/model.py` (이미 작성됨)
  - `load_model()`: `functools.lru_cache`로 프로세스당 1회만 로드
  - `predict(image_source)`: 전처리 + 추론을 수행하고
    `PneumoniaPrediction(is_pneumonia, pneumonia_probability, model_version)`을 반환
  - 모델 버전 식별자: `MODEL_VERSION = "resnet18_daycon_pure_v1"`

### 3.2 입력 전처리 (`worker/model.py`와 동일)

1. 이미지를 RGB로 변환 (`Image.convert("RGB")`)
2. 224×224로 Resize
3. `ToTensor()`
4. ImageNet mean/std로 정규화: `mean=[0.485, 0.456, 0.406]`, `std=[0.229, 0.224, 0.225]`

### 3.3 출력 해석

- 모델은 로짓 1개를 출력하고, `torch.sigmoid()`를 적용해 0~1 확률로 변환한다.
- 이 확률은 **label=1(Pneumonia)일 확률**이다.
- 판정 threshold: `PNEUMONIA_THRESHOLD = 0.5` (검증 시 사용한 것과 동일)

### 3.4 label 매핑 — 프로젝트에서 확정한 기준

`0 = NORMAL`, `1 = PNEUMONIA`

이 매핑은 **데이터셋(`train.csv`)에 텍스트로 명시되어 있는 사실이 아니다.**
다음 근거를 바탕으로 이번 프로젝트의 API 계약으로 확정한 것이다.

1. `train.csv`의 label 분포가 `0: 1,341건 / 1: 3,875건`
2. 이 수치가 공개된 Kermany Chest X-Ray Images (Pneumonia) 데이터셋의
   train 구성(정상 1,341장 / 폐렴 3,875장)과 정확히 일치
3. label=1로 표시된 이미지 일부에서 실제로 폐렴 특유의 편측 혼탁(opacity)
   소견이 육안으로 확인됨

원본 데이터에 공식 문서가 없다는 한계는 11장(설계 결정사항 및 한계)에
다시 명시한다.

### 3.5 검증 결과

| 항목 | 값 |
| --- | --- |
| 검증 데이터 | 783장 (train/validation split, stratified) |
| Accuracy | 0.9962 |
| Recall | 0.9983 |
| Precision | 0.9966 |
| FN | 1 |
| CPU 추론 시간 | 약 0.012초/장 |

검증 데이터 기준으로 NFR-PRED-001의 최소 기준(Recall ≥ 0.90,
Accuracy ≥ 0.80)을 큰 폭으로 충족한다. 단, 이 수치는 학습 프로젝트의
validation split 기준이며 실제 임상 환경이나 다른 X-Ray 장비의 데이터에
대한 성능을 보장하지 않는다.

---

## 4. 데이터 및 결과 저장 구조

### 4.1 기존 테이블 재사용

새 테이블을 만들지 않는다. `app/models/ai_analysis_result.py`에 이미
정의된 `AiAnalysisResult`(테이블명 `ai_analysis_results`)를 그대로 사용한다.

| 컬럼 | 타입 | 비고 |
| --- | --- | --- |
| `id` | BigInteger, PK | |
| `record_id` | BigInteger, FK → `medical_records.id` (ON DELETE CASCADE) | |
| `is_pneumonia` | Boolean | REQ-PRED-001 "폐렴 여부" |
| `confidence` | Numeric(5,2) | REQ-PRED-001 "Confidence" |
| `heatmap_url` | String(255), NOT NULL | REQ-PRED-001 "Hitmap Image URL (선택사항)" — 4.2 참고 |
| `ai_model` | String(50) | `worker.model.MODEL_VERSION` 값을 저장 |
| `created_at` | DateTime | REQ-PRED-002 "예측 수행 일시"로 사용 (별도 컬럼 불필요) |
| `updated_at` | DateTime, nullable | |

`MedicalRecord.ai_analysis_results` relationship(`cascade="all, delete-orphan"`)이
이미 연결되어 있어 진료기록 삭제 시 함께 정리된다.

### 4.2 heatmap_url 처리 방식 (이번 범위: Hitmap 생성 없음)

- 이번 과제 범위에서는 Hitmap(Grad-CAM 등) 이미지를 생성하지 않는다.
- 기존 컬럼이 `NOT NULL`이므로, 마이그레이션 없이 **DB에는 빈 문자열(`""`)을 저장**한다.
- API 응답에서는 빈 문자열을 `null`로 변환해 REQ-PRED-001의 "선택사항" 의미를 유지한다.
- 컬럼을 nullable로 바꾸는 마이그레이션은 이번 Day6 설계 범위에서 작성하지 않는다.

### 4.3 Confidence 정의

"최종 예측 클래스의 확률"로 정의한다.

- `is_pneumonia = true`인 경우: `pneumonia_probability`
- `is_pneumonia = false`인 경우: `1 - pneumonia_probability`

`worker.model.predict()`는 현재 `pneumonia_probability`만 반환하므로, 이
변환은 API 구현 시 **서비스 레이어에서** 수행한다.

### 4.4 중복 방지 — `record_id + ai_model`

- 하나의 `(record_id, ai_model)` 조합에는 하나의 결과만 존재하도록 설계한다.
- 서비스 로직상으로는 추론 전에 기존 결과를 먼저 조회하는 방식으로 구현한다 (7장).
- 설계 방향으로는 DB 레벨 `UniqueConstraint(record_id, ai_model)` 추가를
  전제로 하되, **실제 Alembic migration은 이번 과제 2 범위에서 작성하지
  않는다** (과제 3 또는 별도 DB 작업에서 처리).

> **주의 — Alembic 멀티헤드 확인됨**: 이 프로젝트의 alembic history를
> `alembic heads`로 직접 확인한 결과, 현재 **head가 2개**
> (`20260827_02`, `2a635f4b60e5`) 존재한다. 이후 이 제약을 실제
> migration으로 만들 때는 반드시 먼저 이 멀티헤드 문제를 해결(merge
> revision 또는 올바른 head 지정)한 뒤 진행해야, 새 migration이 잘못된
> 브랜치 위에 얹히는 것을 방지할 수 있다.
>
> **원인 및 기준 계보 확정**: 3일차에 팀원 두 명이 각자 독립적으로
> "초기 스키마" 마이그레이션을 작성해 발생했다 (`2a635f4b60e5`, `20260826_01`).
> 이후 유일하게 계속 이어져 온 쪽은 `20260826_01`(→`20260827_02`)
> 계보이며, 현재 `app/models/*.py`의 실제 컬럼/enum 구조도 이 계보와
> 일치한다. 따라서 **향후 멀티헤드를 해소할 때는 `20260826_01` 계보를
> 기준으로 통일하고, `2a635f4b60e5`(및 그 위에서 갈라진 변경사항)는
> 폐기한다.** 두 계보는 단순 파일 중복이 아니라 `gender`/`department`/`role`
> enum의 DB 타입 이름 자체가 다르므로(`genderenum` vs `gender` 등),
> 병합 migration은 빈 병합이 아니라 실제 스키마 통일 작업을 포함해야
> 한다.

**알려진 기술적 문제 — 동시 요청 시 중복 행 생성 (Day6에서는 미해결, 후속 계획 있음)**

DB에 `UniqueConstraint(record_id, ai_model)`가 없는 상태에서 동일
`(record_id, ai_model)`로 두 요청이 거의 동시에 들어오면, 둘 다 "기존
결과 없음"을 확인하고 각자 추론 후 INSERT에 성공해 **중복 행이 생길 수
있다.** 이는 테스트(`tests/test_prediction_apis.py::test_concurrent_predict_requests_may_create_duplicate_rows`)로
실제로 재현을 확인했다.

Day6에서는 이 문제를 해결하지 않고 다음 후속 계획으로 넘긴다:

1. **DB 환경 구성 단계 (Docker/MySQL 셋업 시)**: 실제 운영 DB(MySQL)
   구성 단계에서 `(record_id, ai_model)`에 대한 `UniqueConstraint`
   migration을 추가하고, 이때 함께 alembic 멀티헤드 문제를 먼저
   해결한다. 서비스 레이어의 추론→저장 로직에도 동시 삽입 충돌
   (`IntegrityError`) 발생 시 기존 결과를 재조회해 반환하는 처리를
   함께 검토/구현한다.
2. **QA 단계**: 동일 진료기록·동일 모델에 대한 동시 요청(부하 테스트
   또는 반복 동시 호출)으로 실제로 중복 행이 더 이상 생기지 않는지
   검증한다. 검증 방법은 `test_concurrent_predict_requests_may_create_duplicate_rows`와
   동일한 접근(동시 POST 후 행 개수 확인)을 운영 DB 환경에서 재실행하는
   것으로 한다.

이번 Day6 production code는 이 후속 계획과 무관하게 수정하지 않았다.

---

## 5. 권한 및 접근 제어

- 기존 `app/apis/dependencies.py`의 `CurrentStaff`를 그대로 사용한다.
  새 권한 dependency를 만들지 않는다.
- `CurrentStaff`는 `User.role`이 `STAFF` 또는 `ADMIN`인지만 검사하며,
  `Department`(MEDICAL/DEV/RESEARCH)는 검사하지 않는다.
- **판단 근거**: `Department` Enum은 `MEDICAL`, `DEV`, `RESEARCH` 세 값이
  전부다. REQ-PRED-001/002가 명시한 "사내 의료인, 개발팀, 연구자"는 이
  세 부서 전체, 즉 "승인된 사내 사용자 전체"와 사실상 같은 대상이다.
  실제로 5일차 설계 문서(`docs/5일차_환자관리_API_설계.md`)에서도
  "의료인"을 "STAFF 또는 ADMIN 역할을 가진 사용자"로 정의했으며 부서로
  구분하지 않았다. 따라서 기존 `CurrentStaff`를 그대로 재사용해도
  REQ-PRED-001/002의 권한 범위를 충족한다.
- 인증 실패: `401 Unauthorized`. 권한 부족/비활성 계정: `403 Forbidden`
  (기존 `get_current_staff`, `get_current_user`의 동작을 그대로 따름).
- **`CurrentMedicalStaff`와의 관계**: `app/apis/dependencies.py`에는
  `CurrentStaff` 외에 `CurrentMedicalStaff`도 이미 존재하며, 이는 `Role`
  검사에 더해 `Department == MEDICAL`(또는 `Role == ADMIN`)까지 검사해
  대상을 의료 부서로 좁힌다. `patient_apis.py`/`medical_record_apis.py`의
  등록(쓰기) API가 이 dependency를 사용한다. 그러나 Day6 REQ-PRED-001은
  "사내 의료인, 개발팀, 연구자" 세 부서 전체를 예측 실행/조회 대상으로
  명시하므로, 대상을 의료 부서로만 좁히는 `CurrentMedicalStaff`는 이
  요구사항 범위와 맞지 않는다. 따라서 두 dependency 중 부서를 가리지
  않는 `CurrentStaff`를 사용하는 것이 REQ-PRED-001의 권한 범위와 정확히
  일치한다.

---

## 6. API 명세

### 6.1 POST — 폐렴 예측 실행 / 결과 조회

| 항목 | 내용 |
| --- | --- |
| 요구사항 ID | REQ-PRED-001 |
| Method | `POST` |
| Endpoint | `/api/v1/medical-records/{record_id}/predictions` |
| 권한 | `CurrentStaff` (Role: STAFF 또는 ADMIN) |
| Path Parameter | `record_id: int` — 진료기록 ID |
| Request Body | 없음 (새 이미지를 업로드하지 않는다) |

**처리 과정**

1. 인증 및 권한 확인 (`CurrentStaff`)
2. `record_id`로 진료기록 조회, X-Ray 이미지 존재 확인
3. `medical_record.xray_images` 중 **첫 번째 이미지**를 예측에 사용한다.
   현재 `XrayImage` relationship에는 명시적인 `order_by`가 없으므로,
   이는 "업로드된 순서가 DB로 보장된다"는 뜻이 아니라 **"현재 구현에서는
   관계에서 반환되는 첫 번째 이미지를 사용하도록 정의한다"**는 설계
   결정이다.
4. `(record_id, ai_model=MODEL_VERSION)` 조합으로 기존 `AiAnalysisResult`
   조회
5. 기존 결과가 있으면 추론을 수행하지 않고 그대로 반환 (`200 OK`)
6. 없으면 X-Ray 파일을 읽어 `worker.model.predict()` 실행 → 4.3 기준으로
   confidence 계산 → `AiAnalysisResult` 저장 (`201 Created`)

**Response**

```json
{
  "id": 11,
  "record_id": 42,
  "is_pneumonia": true,
  "confidence": 99.94,
  "heatmap_url": null,
  "predicted_at": "2026-08-31T16:30:00",
  "model": "resnet18_daycon_pure_v1"
}
```

**HTTP status code**

| 상태 | 조건 |
| --- | --- |
| `201 Created` | 새 예측 결과 생성 |
| `200 OK` | 기존 결과 재사용 |
| `401 Unauthorized` | 인증 실패 |
| `403 Forbidden` | 권한 부족 / 비활성 계정 |
| `404 Not Found` | 진료기록 없음 |
| `409 Conflict` | 진료기록에 X-Ray 이미지가 없음 |
| `422 Unprocessable Entity` | 저장된 파일이 유효한 이미지가 아님 |

### 6.2 GET — 폐렴 예측 결과 목록 조회

| 항목 | 내용 |
| --- | --- |
| 요구사항 ID | REQ-PRED-002 |
| Method | `GET` |
| Endpoint | `/api/v1/medical-records/{record_id}/predictions` |
| 권한 | `CurrentStaff` |
| Path Parameter | `record_id: int` |
| Request Body | 없음 |

**처리 과정**

1. 인증 및 권한 확인
2. 진료기록 존재 확인 (없으면 `404`)
3. 해당 `record_id`의 `AiAnalysisResult` 전체를 조회해 목록으로 반환

**Response** (`200 OK`, 결과 없으면 `[]`)

```json
[
  {
    "id": 11,
    "record_id": 42,
    "is_pneumonia": true,
    "confidence": 99.94,
    "heatmap_url": null,
    "predicted_at": "2026-08-31T16:30:00",
    "model": "resnet18_daycon_pure_v1"
  }
]
```

목록 필드(고유 ID/폐렴 여부/Confidence/Hitmap URL/예측 수행
일시/사용한 모델)는 전부 `AiAnalysisResult`의 기존 컬럼으로 채워진다.

**HTTP status code**

| 상태 | 조건 |
| --- | --- |
| `200 OK` | 정상 조회 (결과 없으면 빈 배열) |
| `401 Unauthorized` | 인증 실패 |
| `403 Forbidden` | 권한 부족 / 비활성 계정 |
| `404 Not Found` | 진료기록 없음 |

---

## 7. 예측 처리 흐름

```
record_id
 → 진료기록 존재 확인 (없으면 404)
 → 진료기록의 X-Ray 존재 확인 (없으면 409)
 → 사용할 모델 버전 확정 (worker.model.MODEL_VERSION)
 → (record_id, ai_model) 기존 결과 조회
     있음 → 그대로 반환 (200, 추론 생략)
     없음 → 첫 번째 X-Ray 이미지 경로 확인
          → worker.model.predict(image_path) 실행
          → is_pneumonia / pneumonia_probability 획득
          → confidence 계산 (4.3 기준)
          → AiAnalysisResult 저장 (heatmap_url="")
          → 반환 (201)
```

---

## 8. 중복 예측 방지 및 기존 결과 재사용

- 판단 키: `record_id + ai_model`
- 같은 진료기록이라도 `ai_model`(=`MODEL_VERSION`)이 다르면 별도 결과로
  취급하고 새로 추론한다. 추후 모델을 교체/개선하면 `MODEL_VERSION`
  문자열을 바꾸는 것만으로 기존 결과와 구분된다.
- 서비스 레이어는 추론 전에 반드시 기존 결과를 먼저 조회한다 (7장).
- DB 레벨 `UniqueConstraint(record_id, ai_model)`을 추가하는 방향으로
  설계하되, 실제 migration은 4.4에서 설명한 대로 이번 문서 범위 밖이다.
  migration 없이 구현할 경우, 동시 요청이 겹치면 중복 행이 생길 수 있다는
  한계가 남는다 (11장에 기록).

---

## 9. 성능 설계 (NFR-PRED-002 — 3초 이내 응답)

- 모델은 애플리케이션 프로세스당 **한 번만 로드**한다
  (`worker.model.load_model()`의 `lru_cache`).
- 검증된 CPU 모델 추론 시간은 약 0.012초/장이다. 이는 모델 추론
  자체가 3초 기준에 충분한 여유가 있음을 보여준다. 실제 API의 3초
  이내 응답 여부는 DB 조회, 파일 I/O 및 HTTP 처리 시간을 포함하여
  Day7 이후 QA 단계에서 검증한다.
- `worker.model.predict()`는 동기(blocking) 함수이므로, FastAPI 비동기
  핸들러에서 직접 호출하지 않고 **`run_in_threadpool`로 감싸서 실행하는
  것으로 설계**한다. 이벤트 루프를 막지 않기 위함이다.
- 기존 결과가 있는 경우 추론을 수행하지 않으므로, 캐시 히트 시에는
  모델 추론 시간을 제외할 수 있다. 실제 3초 이내 응답 여부는 Day7
  이후 QA에서 전체 API 응답시간으로 검증한다.

---

## 10. 오류 처리

기존 프로젝트의 예외 처리 방식(`app/services/medical_record_service.py`
등에서 `HTTPException`을 서비스 레이어에서 직접 raise하는 방식)을 그대로
따른다.

| 상태 코드 | 상황 | 발생 위치 |
| --- | --- | --- |
| `401 Unauthorized` | 인증 토큰 없음/무효 | 기존 `get_current_user` |
| `403 Forbidden` | 권한 부족, 비활성 계정 | 기존 `get_current_staff` |
| `404 Not Found` | 진료기록이 존재하지 않음 | 서비스 레이어 |
| `409 Conflict` | 진료기록에 X-Ray 이미지가 없음 | 서비스 레이어 |
| `422 Unprocessable Entity` | 저장된 파일이 유효한 이미지가 아님(손상 등) | 서비스 레이어 (모델 추론 전처리 단계) |

---

## 11. 설계 결정사항 및 한계

- **X-Ray 이미지 선택**: 여러 장이 저장되어 있어도 이번 설계에서는
  관계에서 반환되는 첫 번째 이미지만 사용한다. DB가 업로드 순서를
  보장하는 것은 아니며, 이는 명시적인 정렬 기준이 정의되기 전까지의
  임시 규칙이다.
- **heatmap_url**: 이번 범위에서 Hitmap을 생성하지 않으며, 컬럼이
  `NOT NULL`이라 빈 문자열로 저장 후 API에서 `null`로 변환한다. 컬럼
  자체를 nullable로 바꾸는 스키마 변경은 하지 않았다.
- **중복 방지의 DB 레벨 보장 부재**: `UniqueConstraint`를 설계 방향으로만
  잡았고 migration은 만들지 않았으므로, 현재 구현에서는 동시 요청 시
  중복 행이 생길 가능성이 남아있다.
- **label 매핑의 근거 성격**: `0=NORMAL, 1=PNEUMONIA`는 데이터셋 출처
  문서가 아니라, label 분포 통계 및 이미지 육안 확인이라는 정황 증거를
  근거로 이번 프로젝트가 확정한 값이다.
- **모델 성능의 적용 범위**: Recall/Accuracy 수치는 팀이 학습에 사용한
  validation split 기준이며, 실제 병원 환경이나 다른 장비로 촬영된
  X-Ray에 대한 성능을 보장하지 않는다.
- **Alembic 멀티헤드**: 4.4에서 설명한 대로 현재 head가 2개 존재하며,
  이번 문서에서 제안한 스키마 변경(nullable 전환, UniqueConstraint 추가
  등)을 실제로 적용하기 전에 별도로 해결이 필요하다.

---

## 12. 참고자료

- [PyTorch 모델 저장하기 & 불러오기](https://tutorials.pytorch.kr/beginner/saving_loading_models.html)
- [Torchvision ResNet18](https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.resnet18.html)
- [Torchvision Transforms](https://docs.pytorch.org/vision/stable/transforms.html)

---

## 13. 후속 작업

Day6에서 발견했지만 이번 범위에서 해결하지 않고 넘긴 항목은 이 문서에
중복해서 관리하지 않고, 프로젝트 루트의 `TODO.md`에서 한곳에 모아
관리한다. 각 항목의 상세 근거는 본문(4.4, 11장)을 참고한다.
