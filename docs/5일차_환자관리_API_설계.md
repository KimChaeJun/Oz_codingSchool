# 5일차 환자 관리 API 설계

## 1. API 개요

환자 정보와 환자의 진료기록을 관리하기 위한 API이다.

모든 API는 로그인한 사용자만 사용할 수 있으며, 환자 정보와 진료기록은 환자 ID를 기준으로 관리한다.

진료기록 등록 시 흉부 X-Ray 이미지를 함께 업로드할 수 있도록 `multipart/form-data` 형식을 사용한다.

---

## 2. 환자 정보 등록 API

### 2-1. 기본 정보

| 항목 | 내용 |
| --- | --- |
| API 이름 | 환자 정보 등록 |
| 설명 | 새로운 환자 정보를 등록한다. |
| 엔드포인트 | `/api/v1/patients` |
| 메서드 | `POST` |
| 인증 필요 여부 | Y |
| Content-Type | `application/json` |

### 2-2. 요청

#### 본문

```json
{
  "name": "홍길동",
  "age": 35,
  "gender": "M",
  "phone": "010-1234-5678"
}
```

| 필드명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| name | string | Y | 환자 이름 |
| age | integer | Y | 환자 나이 |
| gender | string | Y | 성별. `M` 또는 `F` |
| phone | string | Y | 환자 연락처 |

### 2-3. 응답

#### 성공

- `201 Created`

```json
{
  "id": 1,
  "name": "홍길동",
  "age": 35,
  "gender": "M",
  "phone": "010-1234-5678",
  "created_at": "2026-08-28T10:00:00",
  "updated_at": "2026-08-28T10:00:00"
}
```

#### 실패

- `401 Unauthorized`: 로그인하지 않은 사용자
- `409 Conflict`: 중복된 연락처
- `422 Unprocessable Entity`: 필수값 누락 또는 입력 형식 오류

---

## 3. 환자 목록 조회 API

### 3-1. 기본 정보

| 항목 | 내용 |
| --- | --- |
| API 이름 | 환자 목록 조회 |
| 설명 | 등록된 환자 목록을 조회하고 이름, 성별, 나이 범위로 검색·필터링한다. |
| 엔드포인트 | `/api/v1/patients` |
| 메서드 | `GET` |
| 인증 필요 여부 | Y |

### 3-2. 쿼리 파라미터

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| name | string | N | 환자 이름 검색 |
| gender | string | N | `M` 또는 `F` |
| min_age | integer | N | 최소 나이 |
| max_age | integer | N | 최대 나이 |
| page | integer | N | 페이지 번호. 기본값 `1` |
| size | integer | N | 페이지당 개수. 기본값 `20` |

### 3-3. 요청 예시

```text
GET /api/v1/patients?name=홍길동&gender=M&min_age=20&max_age=50&page=1&size=20
```

### 3-4. 응답

#### 성공

- `200 OK`

```json
{
  "items": [
    {
      "id": 1,
      "name": "홍길동",
      "age": 35,
      "gender": "M",
      "phone": "010-1234-5678",
      "created_at": "2026-08-28T10:00:00",
      "updated_at": "2026-08-28T10:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| items | array | 환자 정보 목록 |
| total | integer | 검색 결과 전체 개수 |
| page | integer | 현재 페이지 |
| size | integer | 페이지당 조회 개수 |

---

## 4. 환자 상세 조회 API

### 4-1. 기본 정보

| 항목 | 내용 |
| --- | --- |
| API 이름 | 환자 정보 상세 조회 |
| 설명 | 환자 ID를 기준으로 특정 환자의 정보를 조회한다. |
| 엔드포인트 | `/api/v1/patients/{patient_id}` |
| 메서드 | `GET` |
| 인증 필요 여부 | Y |

### 4-2. 경로 파라미터

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| patient_id | integer | Y | 조회할 환자의 고유 ID |

### 4-3. 응답

#### 성공

- `200 OK`

```json
{
  "id": 1,
  "name": "홍길동",
  "age": 35,
  "gender": "M",
  "phone": "010-1234-5678",
  "created_at": "2026-08-28T10:00:00",
  "updated_at": "2026-08-28T10:00:00"
}
```

#### 실패

- `404 Not Found`

```json
{
  "detail": "환자를 찾을 수 없습니다."
}
```

---

## 5. 환자 정보 수정 API

### 5-1. 기본 정보

| 항목 | 내용 |
| --- | --- |
| API 이름 | 환자 정보 수정 |
| 설명 | 환자 ID를 기준으로 이름과 연락처를 수정한다. |
| 엔드포인트 | `/api/v1/patients/{patient_id}` |
| 메서드 | `PATCH` |
| 인증 필요 여부 | Y |
| Content-Type | `application/json` |

### 5-2. 요청

```json
{
  "name": "김길동",
  "phone": "010-9999-9999"
}
```

| 필드명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| name | string | N | 변경할 환자 이름 |
| phone | string | N | 변경할 연락처 |
|  |  |  | 전달된 필드만 수정한다. |

### 5-3. 응답

#### 성공

- `200 OK`

```json
{
  "id": 1,
  "name": "김길동",
  "age": 35,
  "gender": "M",
  "phone": "010-9999-9999",
  "created_at": "2026-08-28T10:00:00",
  "updated_at": "2026-08-28T11:00:00"
}
```

#### 실패

- `404 Not Found`: 환자를 찾을 수 없음
- `409 Conflict`: 이미 등록된 연락처
- `422 Unprocessable Entity`: 입력 형식 오류

---

## 6. 환자 정보 삭제 API

### 6-1. 기본 정보

| 항목 | 내용 |
| --- | --- |
| API 이름 | 환자 정보 삭제 |
| 설명 | 환자 정보와 관련된 진료기록을 삭제한다. |
| 엔드포인트 | `/api/v1/patients/{patient_id}` |
| 메서드 | `DELETE` |
| 인증 필요 여부 | Y |

### 6-2. 응답

#### 성공

- `204 No Content`

응답 본문을 반환하지 않는다.

#### 실패

- `404 Not Found`

```json
{
  "detail": "환자를 찾을 수 없습니다."
}
```

---

## 7. 진료기록 등록 API

### 7-1. 기본 정보

| 항목 | 내용 |
| --- | --- |
| API 이름 | 진료기록 등록 |
| 설명 | 특정 환자의 진료기록과 흉부 X-Ray 이미지를 등록한다. |
| 엔드포인트 | `/api/v1/patients/{patient_id}/medical-records` |
| 메서드 | `POST` |
| 인증 필요 여부 | Y |
| Content-Type | `multipart/form-data` |

이미지 파일과 입력값을 함께 전송하므로 JSON 요청 본문이 아닌 `multipart/form-data`를 사용한다.

### 7-2. 경로 파라미터

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| patient_id | integer | Y | 진료기록을 등록할 환자 ID |

### 7-3. Form 데이터

| 필드명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| chart_number | string | Y | 진료 차트 번호 |
| symptoms | string | Y | 진료된 증상 |
| xray_image | file | Y | 흉부 X-Ray 이미지 |

### 7-4. 응답

#### 성공

- `201 Created`

```json
{
  "id": 1,
  "patient_id": 1,
  "chart_number": "CHART-20260828-001",
  "symptoms": "기침과 발열이 있습니다.",
  "xray_images": [
  {
    "image_url": "/media/xray/1_chest.png"
  }
],
  "created_at": "2026-08-28T10:30:00",
  "updated_at": "2026-08-28T10:30:00"
}
```

#### 실패

- `404 Not Found`: 환자를 찾을 수 없음
- `413 Request Entity Too Large`: 이미지 용량 초과
- `415 Unsupported Media Type`: 지원하지 않는 이미지 형식
- `422 Unprocessable Entity`: 필수값 누락

---

## 8. 환자별 진료기록 목록 조회 API

### 8-1. 기본 정보

| 항목 | 내용 |
| --- | --- |
| API 이름 | 진료기록 목록 조회 |
| 설명 | 특정 환자에게 등록된 진료기록을 목록으로 조회한다. |
| 엔드포인트 | `/api/v1/patients/{patient_id}/medical-records` |
| 메서드 | `GET` |
| 인증 필요 여부 | Y |

### 8-2. 응답

#### 성공

- `200 OK`

```json
{
  "items": [
    {
      "id": 1,
      "patient_id": 1,
      "chart_number": "CHART-20260828-001",
      "symptoms": "기침과 발열이 있습니다.",
      "created_at": "2026-08-28T10:30:00"
    }
  ],
  "total": 1
}
```

#### 증상 표시 규칙

증상이 100자를 초과하는 경우 목록에서는 일부 내용만 표시하고 `...`으로 줄여서 보여준다.

상세 조회에서는 전체 증상을 확인할 수 있다.

#### 실패

- `404 Not Found`: 환자를 찾을 수 없음

---

## 9. 진료기록 상세 조회 API

### 9-1. 기본 정보

| 항목 | 내용 |
| --- | --- |
| API 이름 | 진료기록 상세 조회 |
| 설명 | 진료기록 ID를 기준으로 진료기록의 전체 정보를 조회한다. |
| 엔드포인트 | `/api/v1/medical-records/{record_id}` |
| 메서드 | `GET` |
| 인증 필요 여부 | Y |

### 9-2. 응답

#### 성공

- `200 OK`

```json
{
  "id": 1,
  "patient_id": 1,
  "chart_number": "CHART-20260828-001",
  "symptoms": "기침과 발열이 있습니다.",
  "xray_images": [
  {
    "image_url": "/media/xray/1_chest.png"
  }
],
  "created_at": "2026-08-28T10:30:00",
  "updated_at": "2026-08-28T10:30:00"
}
```

#### 실패

- `404 Not Found`

```json
{
  "detail": "진료기록을 찾을 수 없습니다."
}
```

---

## 10. 진료기록 수정 API

### 10-1. 기본 정보

| 항목 | 내용 |
| --- | --- |
| API 이름 | 진료기록 수정 |
| 설명 | 진료기록의 차트 번호와 증상을 수정한다. |
| 엔드포인트 | `/api/v1/medical-records/{record_id}` |
| 메서드 | `PATCH` |
| 인증 필요 여부 | Y |
| Content-Type | `application/json` |

### 10-2. 요청

```json
{
  "chart_number": "CHART-20260828-002",
  "symptoms": "기침, 발열 및 호흡 곤란이 있습니다."
}
```

| 필드명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| chart_number | string | N | 변경할 차트 번호 |
| symptoms | string | N | 변경할 증상 |
|  |  |  | 전달된 필드만 수정한다. |

### 10-3. 응답

#### 성공

- `200 OK`

진료기록 상세 조회와 같은 형식으로 수정된 정보를 반환한다.

#### 실패

- `404 Not Found`: 진료기록을 찾을 수 없음
- `422 Unprocessable Entity`: 입력 형식 오류

---

## 11. 진료기록 삭제 API

### 11-1. 기본 정보

| 항목 | 내용 |
| --- | --- |
| API 이름 | 진료기록 삭제 |
| 설명 | 진료기록과 연결된 X-Ray 이미지를 삭제한다. |
| 엔드포인트 | `/api/v1/medical-records/{record_id}` |
| 메서드 | `DELETE` |
| 인증 필요 여부 | Y |

### 11-2. 응답

#### 성공

- `204 No Content`

응답 본문을 반환하지 않는다.

#### 실패

- `404 Not Found`: 진료기록을 찾을 수 없음

---

## 12. 공통 오류 형식

입력값 검증 오류가 발생하면 FastAPI의 기본 검증 오류 형식을 사용한다.

```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

| 상태 코드 | 의미 |
| --- | --- |
| 401 | 로그인 또는 인증이 필요함 |
| 403 | API를 실행할 권한이 없음 |
| 404 | 환자 또는 진료기록을 찾을 수 없음 |
| 409 | 중복된 데이터 |
| 413 | 업로드 파일 크기 초과 |
| 415 | 지원하지 않는 파일 형식 |
| 422 | 요청 데이터 형식 오류 |
| 500 | 서버 내부 오류 |

---

## 13. API 목록

| 메서드 | 엔드포인트 | 설명 |
| --- | --- | --- |
| POST | `/api/v1/patients` | 환자 정보 등록 |
| GET | `/api/v1/patients` | 환자 목록 조회 |
| GET | `/api/v1/patients/{patient_id}` | 환자 상세 조회 |
| PATCH | `/api/v1/patients/{patient_id}` | 환자 정보 수정 |
| DELETE | `/api/v1/patients/{patient_id}` | 환자 정보 삭제 |
| POST | `/api/v1/patients/{patient_id}/medical-records` | 진료기록 등록 |
| GET | `/api/v1/patients/{patient_id}/medical-records` | 진료기록 목록 조회 |
| GET | `/api/v1/medical-records/{record_id}` | 진료기록 상세 조회 |
| PATCH | `/api/v1/medical-records/{record_id}` | 진료기록 수정 |
| DELETE | `/api/v1/medical-records/{record_id}` | 진료기록 삭제 |