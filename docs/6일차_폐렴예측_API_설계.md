# 6일차 폐렴 예측 API 설계

## 1. API 개요

진료기록에 연결된 흉부 X-Ray 이미지를 AI 모델로 분석하여 폐렴 여부와 예측 신뢰도를 제공하는 API이다.

로그인한 사용자만 사용할 수 있으며, 의료진(`MEDICAL`), 개발팀(`DEV`), 연구자(`RESEARCH`) 권한을 가진 사용자만 이용할 수 있다.

### 주요 기능

- 진료기록을 기준으로 폐렴 예측 요청
- 흉부 X-Ray 이미지 업로드
- 폐렴 예측 결과 저장
- 저장된 예측 결과 조회
- 같은 진료기록과 같은 모델의 결과가 있으면 재추론하지 않고 기존 결과 반환
- 폐렴 여부, 신뢰도, 사용 모델, 예측 시간을 응답

---

## 2. 폐렴 예측 API

### 2-1. API 기본 정보

| 항목 | 내용 |
|---|---|
| API 이름 | 폐렴 예측 API |
| 설명 | 흉부 X-Ray 이미지를 AI 모델로 분석하여 폐렴 여부를 예측한다. |
| 엔드포인트 | `/api/v1/medical-records/{record_id}/prediction` |
| 메서드 | `POST` |
| 인증 필요 여부 | Y |
| 허용 권한 | `MEDICAL`, `DEV`, `RESEARCH` |
| 요청 형식 | `multipart/form-data` |
| 응답 형식 | `application/json` |

### 2-2. 요청

#### Headers

| Key | Value | 설명 |
|---|---|---|
| Authorization | `Bearer {access_token}` | 로그인 후 발급받은 액세스 토큰 |
| Content-Type | `multipart/form-data` | 이미지 파일을 포함한 요청 |

#### Path Parameter

| 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `record_id` | integer | Y | 폐렴 예측을 요청할 진료기록 ID |

#### Request Body

| 필드명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `xray_image` | file | Y | 폐렴 예측에 사용할 흉부 X-Ray 이미지 |

#### 요청 예시

```bash
curl -X POST \
  "http://127.0.0.1:8001/api/v1/medical-records/1/prediction" \
  -H "Authorization: Bearer {access_token}" \
  -F "xray_image=@chest_xray.png"
```

### 2-3. 처리 과정

1. 액세스 토큰의 유효성을 확인한다.
2. 사용자의 권한이 허용된 권한인지 확인한다.
3. `record_id`에 해당하는 진료기록을 조회한다.
4. 업로드된 파일이 이미지 파일인지 확인한다.
5. 동일한 진료기록에 같은 AI 모델의 예측 결과가 이미 저장되어 있는지 확인한다.
6. 기존 결과가 있으면 AI 모델을 다시 실행하지 않고 기존 결과를 반환한다.
7. 기존 결과가 없으면 X-Ray 이미지를 AI 모델 입력 형식으로 변환한다.
8. AI 모델을 이용하여 폐렴 여부와 신뢰도를 계산한다.
9. 예측 결과를 데이터베이스에 저장한다.
10. 저장된 예측 결과를 응답한다.

### 2-4. 성공 응답

#### 신규 예측

- `201 Created`

```json
{
  "id": 1,
  "medical_record_id": 10,
  "is_pneumonia": true,
  "confidence": 0.95,
  "heatmap_url": null,
  "predicted_at": "2026-08-31T12:00:00Z",
  "model_name": "SimpleCNN"
}
```

#### 기존 예측 결과 반환

- `200 OK`

동일한 진료기록과 같은 AI 모델의 예측 결과가 이미 저장되어 있는 경우에는 재추론하지 않고 기존 결과를 반환한다.

### 2-5. 응답 필드

| 필드명 | 타입 | 설명 |
|---|---|---|
| `id` | integer | AI 예측 결과 ID |
| `medical_record_id` | integer | 진료기록 ID |
| `is_pneumonia` | boolean | 폐렴 여부 |
| `confidence` | number | AI 모델의 예측 신뢰도 |
| `heatmap_url` | string 또는 null | 예측 근거 이미지 주소 |
| `predicted_at` | datetime | 예측 수행 일시 |
| `model_name` | string | 사용한 AI 모델 이름 |

### 2-6. 실패 응답

#### 401 Unauthorized

인증 토큰이 없거나 유효하지 않은 경우

```json
{
  "detail": "인증이 필요합니다."
}
```

#### 403 Forbidden

허용되지 않은 권한의 사용자가 요청한 경우

```json
{
  "detail": "폐렴 예측 API를 사용할 권한이 없습니다."
}
```

#### 404 Not Found

진료기록을 찾을 수 없는 경우

```json
{
  "detail": "진료기록을 찾을 수 없습니다."
}
```

#### 400 Bad Request

진료기록에 연결된 X-Ray 이미지가 없는 경우

```json
{
  "detail": "진료기록에 연결된 X-Ray 이미지가 없습니다."
}
```

#### 413 Request Entity Too Large

업로드한 파일의 크기가 허용 범위를 초과한 경우

```json
{
  "detail": "이미지 파일 크기가 제한을 초과했습니다."
}
```

#### 415 Unsupported Media Type

지원하지 않는 파일 형식인 경우

```json
{
  "detail": "지원하지 않는 이미지 형식입니다."
}
```

#### 422 Unprocessable Entity

필수 요청 값이 누락되거나 형식이 올바르지 않은 경우

```json
{
  "detail": "요청 형식이 올바르지 않습니다."
}
```

#### 500 Internal Server Error

AI 모델 실행 또는 예측 결과 저장 중 오류가 발생한 경우

```json
{
  "detail": "폐렴 예측 처리 중 오류가 발생했습니다."
}
```

---

## 3. 폐렴 예측 결과 조회 API

### 3-1. API 기본 정보

| 항목 | 내용 |
|---|---|
| API 이름 | 폐렴 예측 결과 조회 API |
| 설명 | 진료기록에 저장된 AI 폐렴 예측 결과를 조회한다. |
| 엔드포인트 | `/api/v1/medical-records/{record_id}/prediction` |
| 메서드 | `GET` |
| 인증 필요 여부 | Y |
| 허용 권한 | `MEDICAL`, `DEV`, `RESEARCH` |
| 응답 형식 | `application/json` |

### 3-2. 요청

#### Headers

| Key | Value | 설명 |
|---|---|---|
| Authorization | `Bearer {access_token}` | 로그인 후 발급받은 액세스 토큰 |

#### Path Parameter

| 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `record_id` | integer | Y | 예측 결과를 조회할 진료기록 ID |

#### 요청 예시

```bash
curl -X GET \
  "http://127.0.0.1:8001/api/v1/medical-records/1/prediction" \
  -H "Authorization: Bearer {access_token}"
```

### 3-3. 성공 응답

- `200 OK`

```json
{
  "id": 1,
  "medical_record_id": 10,
  "is_pneumonia": true,
  "confidence": 0.95,
  "heatmap_url": null,
  "predicted_at": "2026-08-31T12:00:00Z",
  "model_name": "SimpleCNN"
}
```

### 3-4. 실패 응답

#### 401 Unauthorized

```json
{
  "detail": "인증이 필요합니다."
}
```

#### 403 Forbidden

```json
{
  "detail": "폐렴 예측 결과를 조회할 권한이 없습니다."
}
```

#### 404 Not Found

진료기록 또는 예측 결과를 찾을 수 없는 경우

```json
{
  "detail": "예측 결과를 찾을 수 없습니다."
}
```

---

## 4. AI 모델 평가 기준

AI 모델은 폐렴 환자를 정상으로 잘못 판단하는 상황을 줄이는 것을 중요하게 평가한다.

### 4-1. 혼동 행렬

| 구분 | 설명 |
|---|---|
| TP | 실제 폐렴 환자를 폐렴으로 예측 |
| FP | 실제 정상인을 폐렴으로 예측 |
| FN | 실제 폐렴 환자를 정상으로 예측 |
| TN | 실제 정상인을 정상으로 예측 |

### 4-2. Recall

실제 폐렴 환자 중에서 폐렴으로 올바르게 예측한 비율이다.

```text
Recall = TP / (TP + FN)
```

목표 기준은 `0.90 이상`이다.

### 4-3. Accuracy

전체 예측 결과 중에서 올바르게 예측한 비율이다.

```text
Accuracy = (TP + TN) / 전체 샘플 수
```

보조 평가 지표로 사용하며 목표 기준은 `0.80 이상`이다.

---

## 5. 비기능 요구사항

### 5-1. API 응답 시간

- 모든 폐렴 예측 API는 최대 3초 이내에 응답해야 한다.
- 동일한 진료기록과 같은 AI 모델의 결과가 이미 저장되어 있으면 재추론하지 않는다.
- AI 모델은 서버 실행 시 메모리에 한 번만 불러온다.

### 5-2. 보안

- 모든 API는 로그인한 사용자만 사용할 수 있다.
- 액세스 토큰은 `Authorization` 헤더의 `Bearer` 방식으로 전달한다.
- 허용된 권한을 가진 사용자만 폐렴 예측 및 결과 조회를 할 수 있다.
- 업로드된 파일은 허용된 이미지 형식인지 확인한다.
- 비밀번호나 인증 토큰과 같은 민감한 정보는 응답에 포함하지 않는다.

### 5-3. 데이터 저장

- 예측 결과는 진료기록과 연결하여 저장한다.
- 예측 결과에는 폐렴 여부, 신뢰도, 예측 시간, 사용 모델을 저장한다.
- 히트맵을 생성하지 않는 경우 `heatmap_url`은 `null`로 저장한다.
- 같은 진료기록과 같은 모델의 결과가 이미 있으면 중복 저장하지 않는다.