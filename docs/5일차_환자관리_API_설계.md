# 5일차 환자 관리 및 진료기록 API 설계

## 1. 설계 개요

5일차 사용자 요구사항 정의(URD)를 바탕으로 환자 관리 및 진료기록 관리 API를 설계합니다.
4일차 User API와 동일한 계층 구조를 따릅니다.

---

## 2. 데이터 모델

### 2.1 Patient

- id: 환자 고유 식별자
- name: 환자 이름
- age: 환자 나이
- gender: 성별 (M 또는 F)
- phone: 연락처
- created_at: 생성 일시
- updated_at: 수정 일시

### 2.2 MedicalRecord

- id: 진료 기록 고유 식별자
- patient_id: 환자 고유 ID (Patient 참조)
- chart_number: 진료 차트 넘버
- symptoms: 진료된 증상
- created_at: 생성 일시
- updated_at: 수정 일시

### 2.3 XrayImage

- id: X-Ray 이미지 고유 식별자
- record_id: 진료 기록 고유 ID (MedicalRecord 참조)
- image_url: 로컬 저장소 경로

---

## 3. 모델 간 관계

- Patient (1) ← → (N) MedicalRecord
- MedicalRecord (1) ← → (N) XrayImage

**삭제 정책:**
- Patient 삭제 시: 관련 MedicalRecord, XrayImage 데이터 삭제
- Patient 삭제 시: 로컬 저장소의 X-Ray 이미지 파일 영구 삭제

---

## 4. 권한 및 역할

### 권한 정의

**의료인:** STAFF 또는 ADMIN 역할을 가진 사용자
- 환자 정보 등록 (REQ-PTNT-001)
- 진료기록 등록 (REQ-MDR-001)

**로그인된 사내 인원:** 사내 개발진, 의료 실무진, 연구진
- 환자 목록 조회 (REQ-PTNT-002)
- 환자 상세 조회 (REQ-PTNT-003)
- 환자 정보 수정 (REQ-PTNT-004)
- 환자 정보 삭제 (REQ-PTNT-005)
- 진료기록 목록 조회 (REQ-MDR-002)
- 진료기록 상세 조회 (REQ-MDR-003)

---

## 5. Patient API

### 5.1 환자 정보 등록

**기본 정보**

- 요구사항 ID: REQ-PTNT-001
- Method: POST
- Endpoint: `/api/v1/patients`
- 권한: 의료인

**Request Body**

```json
{
  "name": "홍길동",
  "age": 45,
  "gender": "M",
  "phone": "01012345678"
}
```

**필수 입력 항목**

| 항목 | 설명 |
|------|------|
| name | 환자 이름 |
| age | 환자 나이 |
| gender | 성별 (M 또는 F) |
| phone | 연락처 |

**Response**

**201 Created**

---

### 5.2 환자 목록 조회

**기본 정보**

- 요구사항 ID: REQ-PTNT-002
- Method: GET
- Endpoint: `/api/v1/patients`
- 권한: 로그인된 사내 인원

**Query Parameters**

| 파라미터 | 설명 |
|---------|------|
| search | 환자 이름 검색 (부분 매칭) |
| gender | 성별 필터 (M 또는 F) |
| age_min | 최소 나이 |
| age_max | 최대 나이 |

**Response**

**200 OK**

**조회 필드**

- 환자 고유 ID
- 이름
- 나이
- 성별
- 연락처
- 생성일시
- 수정일시

---

### 5.3 환자 상세 조회

**기본 정보**

- 요구사항 ID: REQ-PTNT-003
- Method: GET
- Endpoint: `/api/v1/patients/{patient_id}`
- 권한: 로그인된 사내 인원

**Path Parameters**

| 파라미터 | 설명 |
|---------|------|
| patient_id | 환자 ID |

**Response**

**200 OK**

**조회 항목**

- 이름
- 성별
- 연락처
- 나이

---

### 5.4 환자 정보 수정

**기본 정보**

- 요구사항 ID: REQ-PTNT-004
- Method: PATCH
- Endpoint: `/api/v1/patients/{patient_id}`
- 권한: 로그인된 사내 인원

**Path Parameters**

| 파라미터 | 설명 |
|---------|------|
| patient_id | 환자 ID |

**Request Body**

```json
{
  "name": "홍길동 (수정)",
  "phone": "01087654321"
}
```

**수정 가능 항목**

- 이름
- 연락처

**Response**

**200 OK**

---

### 5.5 환자 정보 삭제

**기본 정보**

- 요구사항 ID: REQ-PTNT-005
- Method: DELETE
- Endpoint: `/api/v1/patients/{patient_id}`
- 권한: 로그인된 사내 인원

**Path Parameters**

| 파라미터 | 설명 |
|---------|------|
| patient_id | 환자 ID |

**Response**

**204 No Content**

**삭제 동작**

- 해당 환자 데이터 삭제
- 관련 진료기록 데이터 삭제
- 관련 X-Ray 이미지 데이터 삭제
- 로컬 저장소의 X-Ray 이미지 파일 영구 삭제

---

## 6. MedicalRecord API

### 6.1 진료기록 등록

**기본 정보**

- 요구사항 ID: REQ-MDR-001
- Method: POST
- Endpoint: `/api/v1/medical-records`
- 권한: 의료인
- Content-Type: `multipart/form-data`

**필수 입력 항목**

| 항목 | 설명 |
|------|------|
| patient_id | 환자 고유 ID |
| chart_number | 진료 차트 넘버 |
| symptoms | 진료된 증상 |
| xray_image | 촬영된 흉부 X-Ray 이미지 |

**X-Ray 이미지 요구사항**

- 촬영된 흉부 X-Ray 이미지를 필수로 업로드
- 업로드 시 업로드된 이미지의 미리보기 제공
- 이미지 파일은 서버가 실행되는 환경의 로컬 저장소에 저장
- DB에는 이미지 파일의 참조 경로만 저장

**shooting_datetime 처리**

- `xray_images.shooting_datetime`은 3일차 DB 설계상 `NOT NULL` 컬럼이나, 본 API의 요청 항목에는 포함하지 않는다.
- 클라이언트가 별도로 입력하지 않으며, 서버가 진료기록 등록을 처리하는 시각을 자동으로 저장한다.

**Response**

**201 Created**

---

### 6.2 진료기록 목록 조회

**기본 정보**

- 요구사항 ID: REQ-MDR-002
- Method: GET
- Endpoint: `/api/v1/patients/{patient_id}/medical-records`
- 권한: 로그인된 사내 인원

**Path Parameters**

| 파라미터 | 설명 |
|---------|------|
| patient_id | 환자 ID |

**Response**

**200 OK**

**조회 필드**

- 진료 기록 ID
- 차트 넘버
- 증상 (100자 초과 시 100자까지만 표시하고 생략 표시 `…` 추가)
- 생성일시

---

### 6.3 진료기록 상세 조회

**기본 정보**

- 요구사항 ID: REQ-MDR-003
- Method: GET
- Endpoint: `/api/v1/medical-records/{record_id}`
- 권한: 로그인된 사내 인원

**Path Parameters**

| 파라미터 | 설명 |
|---------|------|
| record_id | 진료기록 ID |

**Response**

**200 OK**

**조회 필드**

- 진료 기록 ID
- 차트 넘버
- 증상 (전체)
- 흉부 X-Ray 이미지
- 생성일시

---

## 7. 비기능 요구사항

| 항목 | 요구사항 |
|------|---------|
| 환자 관련 API 응답 시간 (NFR-PTNT-001) | 최대 3초 이내 |
| 진료기록 관련 API 응답 시간 (NFR-MDR-001) | 최대 3초 이내 |

---

## 8. 계층 구조

5일차 API는 4일차 User API와 동일한 계층 구조를 따릅니다:

- API Layer: HTTP 요청 처리 및 응답
- Service Layer: 비즈니스 로직 처리
- Repository Layer: 데이터 접근
- Database: SQLAlchemy ORM을 통한 데이터 관리

---

## 9. 구현 범위

**총 8개 API:**
- Patient: 등록, 목록 조회, 상세 조회, 수정, 삭제 (5개)
- MedicalRecord: 등록, 목록 조회, 상세 조회 (3개)

**핵심 구현 사항:**
- X-Ray 이미지 로컬 저장소 저장 및 경로 관리
- 환자 삭제 시 로컬 저장소 파일 함께 삭제 처리
