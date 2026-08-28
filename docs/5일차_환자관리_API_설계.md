# 5일차 환자관리 API 설계

## 📋 개요
의료 기관의 환자 정보와 진료 데이터를 통합 관리하는 백엔드 시스템입니다.

## 🎯 주요 기능
- 환자 정보 관리 (등록, 조회, 수정, 삭제)
- 진료기록 추적 (진료 내용, 증상 기록)
- X-Ray 이미지 저장 및 관리
- 페이징과 필터링을 통한 효율적인 데이터 검색
- Cascade Delete로 데이터 무결성 보장

## 📊 API 명세

### 환자 관리 API (5개)

#### 1. 환자 등록
```http
POST /api/v1/patients
Content-Type: application/json

{
  "name": "홍길동",
  "age": 35,
  "gender": "M",
  "phone": "010-1234-5678"
}

Response: 201 Created
{
  "id": 1,
  "name": "홍길동",
  "age": 35,
  "gender": "M",
  "phone": "010-1234-5678",
  "created_at": "2026-08-28T21:52:32",
  "updated_at": "2026-08-28T21:52:32"
}
```

#### 2. 환자 목록 조회
```http
GET /api/v1/patients?page=1&size=20&name=홍&gender=M&age=35

Response: 200 OK
{
  "items": [...],
  "total": 1,
  "page": 1,
  "size": 20
}
```

#### 3. 환자 상세 조회
```http
GET /api/v1/patients/{patient_id}

Response: 200 OK
{
  "id": 1,
  "name": "홍길동",
  "age": 35,
  "gender": "M",
  "phone": "010-1234-5678",
  "created_at": "2026-08-28T21:52:32",
  "updated_at": "2026-08-28T21:52:32"
}
```

#### 4. 환자 정보 수정
```http
PATCH /api/v1/patients/{patient_id}
Content-Type: application/json

{
  "name": "김철수",
  "age": 36
}

Response: 200 OK
{
  "id": 1,
  "name": "김철수",
  "age": 36,
  "gender": "M",
  "phone": "010-1234-5678",
  "created_at": "2026-08-28T21:52:32",
  "updated_at": "2026-08-29T10:00:00"
}
```

#### 5. 환자 정보 삭제
```http
DELETE /api/v1/patients/{patient_id}

Response: 204 No Content
```

### 진료기록 API (5개)

#### 6. 진료기록 등록 (X-Ray 이미지 포함)
```http
POST /api/v1/patients/{patient_id}/medical-records
Content-Type: multipart/form-data

Form Data:
- chart_number: "2026-001"
- symptoms: "두통, 발열"
- xray_images: [파일1, 파일2, ...]

Response: 201 Created
{
  "id": 1,
  "patient_id": 1,
  "chart_number": "2026-001",
  "symptoms": "두통, 발열",
  "xray_images": [
    {"id": 1, "image_url": "/uploads/xray_001.jpg"}
  ],
  "created_at": "2026-08-28T21:52:32",
  "updated_at": "2026-08-28T21:52:32"
}
```

#### 7. 진료기록 목록 조회
```http
GET /api/v1/patients/{patient_id}/medical-records?page=1&size=20

Response: 200 OK
{
  "items": [
    {
      "id": 1,
      "patient_id": 1,
      "chart_number": "2026-001",
      "symptoms": "두통, 발열",  // 100자 제한
      "xray_images": [...],
      "created_at": "2026-08-28T21:52:32",
      "updated_at": "2026-08-28T21:52:32"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

#### 8. 진료기록 상세 조회
```http
GET /api/v1/medical-records/{record_id}

Response: 200 OK
{
  "id": 1,
  "patient_id": 1,
  "chart_number": "2026-001",
  "symptoms": "두통, 발열, 오한 증상 나타남",  // 전체 내용
  "xray_images": [
    {"id": 1, "image_url": "/uploads/xray_001.jpg"},
    {"id": 2, "image_url": "/uploads/xray_002.jpg"}
  ],
  "created_at": "2026-08-28T21:52:32",
  "updated_at": "2026-08-28T21:52:32"
}
```

#### 9. 진료기록 수정
```http
PATCH /api/v1/medical-records/{record_id}
Content-Type: multipart/form-data

Form Data:
- chart_number: "2026-001-Rev1"
- symptoms: "두통 완화, 발열 지속"
- xray_images: [새로운 파일들]

Response: 200 OK
{...}
```

#### 10. 진료기록 삭제
```http
DELETE /api/v1/medical-records/{record_id}

Response: 204 No Content
```

## 📊 데이터 모델

### Patient (환자)
```
- id (BIGINT, PK)
- name (VARCHAR(100))
- age (INT)
- gender (ENUM: M, F)
- phone (VARCHAR(20))
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
```

### MedicalRecord (진료기록)
```
- id (BIGINT, PK)
- patient_id (BIGINT, FK)
- chart_number (VARCHAR(100))
- symptoms (TEXT)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
```

### XrayImage (X-Ray 이미지)
```
- id (BIGINT, PK)
- record_id (BIGINT, FK)
- image_url (VARCHAR(255))
- created_at (TIMESTAMP)
```

## ✅ 요구사항

- 페이징: page, size 파라미터 지원
- 필터링: 이름, 성별, 나이로 필터링
- 파일 업로드: 최대 10MB, jpg/png/jpeg 지원
- 증상 100자 제한: 목록 조회에서만 제한 (상세 조회는 전체)
- Cascade Delete: 환자 삭제 시 진료기록 자동 삭제
- 오류 처리: 401, 403, 404, 409, 413, 415, 422 상태코드

## 🔧 기술 스택
- FastAPI
- SQLAlchemy ORM
- MySQL
- Docker & Docker Compose
- Swagger UI