# 4일차 - User API 설계

## 1. 회원가입 API

### 1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 회원가입 API |
| 설명 | 사용자가 User 서비스에 회원가입한다. |
| 엔드포인트 | `/api/v1/users` |
| 메서드 | `POST` |
| 인증 필요 여부 | N |

### 2. 요청

#### Headers

| Key | Value | 설명 |
|---|---|---|
| Content-Type | `application/json` | JSON 형식의 회원정보 전달 |

#### 본문 필드

| 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| email | string | Y | 사용자 이메일 |
| password | string | Y | 사용자 비밀번호 |
| name | string | Y | 사용자 이름 |
| department | string | Y | `RESEARCH`, `MEDICAL`, `DEV` |
| gender | string | Y | `M` 또는 `F` |
| phone_number | string | Y | 휴대폰 번호 |

#### 요청 예시

```json
{
  "email": "user@example.com",
  "password": "password123!",
  "name": "홍길동",
  "department": "DEV",
  "gender": "M",
  "phone_number": "01012345678"
}
```

### 3. 응답

#### 성공

- `201 Created`

```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "홍길동",
  "department": "DEV",
  "gender": "M",
  "phone_number": "01012345678",
  "role": "PENDING",
  "is_active": true
}
```

비밀번호는 응답에 포함하지 않는다.

#### 실패

- `409 Conflict`: 이미 존재하는 이메일 또는 전화번호
- `422 Unprocessable Entity`: 필수값 누락 또는 형식 오류

### 4. 비고

- 회원가입 시 기본 권한은 `PENDING`으로 설정한다.
- 비밀번호는 해시하여 저장한다.

---

## 2. 로그인 API

### 1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 로그인 API |
| 설명 | 이메일과 비밀번호를 확인하고 JWT를 발급한다. |
| 엔드포인트 | `/api/v1/auth/login` |
| 메서드 | `POST` |
| 인증 필요 여부 | N |

### 2. 요청

#### Headers

| Key | Value | 설명 |
|---|---|---|
| Content-Type | `application/json` | 로그인 정보 전달 |

#### 본문 필드

| 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| email | string | Y | 가입한 이메일 |
| password | string | Y | 비밀번호 |

#### 요청 예시

```json
{
  "email": "user@example.com",
  "password": "password123!"
}
```

### 3. 응답

#### 성공

- `200 OK`

```json
{
  "access_token": "access-token-value",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "홍길동",
    "role": "STAFF"
  }
}
```

#### 응답 Headers

| Key | 예시 값 | 설명 |
|---|---|---|
| Set-Cookie | `refresh_token=<JWT>; HttpOnly; Secure; SameSite=Lax; Max-Age=604800` | 7일 동안 유효한 리프레시 토큰 |

#### 실패

- `401 Unauthorized`

```json
{
  "detail": "이메일 또는 비밀번호가 일치하지 않습니다."
}
```

- `403 Forbidden`

```json
{
  "detail": "비활성화된 사용자입니다."
}
```

- `422 Unprocessable Entity`: 필수값 누락 또는 형식 오류

### 4. 비고

- 액세스 토큰은 30분 동안 유효하다.
- 리프레시 토큰은 7일 동안 유효하다.
- JWT payload에는 최소 정보인 `user_id`만 저장한다.

---

## 3. 액세스 토큰 재발급 API

### 1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 액세스 토큰 재발급 API |
| 설명 | 리프레시 토큰을 사용하여 액세스 토큰을 재발급한다. |
| 엔드포인트 | `/api/v1/auth/refresh` |
| 메서드 | `POST` |
| 인증 필요 여부 | 리프레시 토큰 필요 |

### 2. 요청

#### Headers

| Key | Value | 설명 |
|---|---|---|
| Cookie | `refresh_token=<JWT>` | 리프레시 토큰 전달 |

#### 본문 필드

| 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| - | - | N | 요청 본문을 사용하지 않음 |

### 3. 응답

#### 성공

- `200 OK`

```json
{
  "access_token": "new-access-token-value",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### 실패

- `401 Unauthorized`

```json
{
  "detail": "유효하지 않거나 만료된 리프레시 토큰입니다."
}
```

### 4. 비고

리프레시 토큰까지 만료되면 다시 로그인해야 한다.

---

## 4. 로그아웃 API

### 1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 로그아웃 API |
| 설명 | 로그인한 사용자를 로그아웃 처리한다. |
| 엔드포인트 | `/api/v1/auth/logout` |
| 메서드 | `POST` |
| 인증 필요 여부 | Y |

### 2. 요청

#### Headers

| Key | Value | 설명 |
|---|---|---|
| Authorization | `Bearer <access_token>` | 로그인 사용자 인증 |
| Cookie | `refresh_token=<JWT>` | 리프레시 토큰 삭제 대상 |

#### 본문 필드

| 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| - | - | N | 요청 본문을 사용하지 않음 |

### 3. 응답

#### 성공

- `204 No Content`

로그아웃 시 리프레시 토큰 쿠키를 삭제한다.

#### 실패

- `401 Unauthorized`: 유효하지 않은 액세스 토큰

### 4. 비고

로그아웃 이후 기존 토큰은 사용할 수 없도록 처리한다.

---

## 5. 회원 목록 조회 API

### 1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 회원 목록 조회 API |
| 설명 | 관리자가 전체 회원을 조회한다. |
| 엔드포인트 | `/api/v1/users` |
| 메서드 | `GET` |
| 인증 필요 여부 | 관리자 권한 필요 |

### 2. 요청

#### Headers

| Key | Value | 설명 |
|---|---|---|
| Authorization | `Bearer <access_token>` | 관리자 인증 |

#### 쿼리 파라미터

| 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| keyword | string | N | 이메일 또는 이름 검색 |
| department | string | N | 부서별 필터 |
| page | integer | N | 페이지 번호 |
| size | integer | N | 페이지당 회원 수 |

#### 요청 예시

```text
GET /api/v1/users?keyword=홍길동&department=DEV&page=1&size=20
```

### 3. 응답

#### 성공

- `200 OK`

```json
{
  "items": [
    {
      "id": 1,
      "email": "user@example.com",
      "name": "홍길동",
      "department": "DEV",
      "gender": "M",
      "phone_number": "01012345678",
      "role": "STAFF",
      "is_active": true
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

#### 실패

- `401 Unauthorized`: 인증되지 않은 사용자
- `403 Forbidden`: 관리자 권한 없음
- `422 Unprocessable Entity`: 잘못된 검색 조건

### 4. 비고

비밀번호와 비밀번호 해시값은 응답에 포함하지 않는다.

---

## 6. 회원 권한 변경 API

### 1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 회원 권한 변경 API |
| 설명 | 관리자가 회원의 권한을 변경한다. |
| 엔드포인트 | `/api/v1/users/{user_id}/role` |
| 메서드 | `PATCH` |
| 인증 필요 여부 | 관리자 권한 필요 |

### 2. 요청

#### Headers

| Key | Value | 설명 |
|---|---|---|
| Authorization | `Bearer <access_token>` | 관리자 인증 |
| Content-Type | `application/json` | 변경할 권한 전달 |

#### 본문 필드

| 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| role | string | Y | `PENDING`, `STAFF`, `ADMIN` |

#### Path Parameter

| 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| user_id | integer | Y | 권한을 변경할 사용자 ID |

### 3. 응답

#### 성공

- `200 OK`

```json
{
  "id": 1,
  "role": "STAFF"
}
```

#### 실패

- `403 Forbidden`: 관리자 권한 없음
- `404 Not Found`: 사용자를 찾을 수 없음
- `422 Unprocessable Entity`: 잘못된 권한 값

---

## 7. 마이페이지 조회 API

### 1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 마이페이지 조회 API |
| 설명 | 로그인한 사용자가 자신의 정보를 조회한다. |
| 엔드포인트 | `/api/v1/users/me` |
| 메서드 | `GET` |
| 인증 필요 여부 | Y |

### 2. 요청

#### Headers

| Key | Value | 설명 |
|---|---|---|
| Authorization | `Bearer <access_token>` | 로그인 사용자 인증 |

#### 쿼리 파라미터

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| 없음 | - | N | 쿼리 파라미터를 사용하지 않음 |

### 3. 응답

#### 성공

- `200 OK`

```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "홍길동",
  "department": "DEV",
  "gender": "M",
  "phone_number": "01012345678",
  "role": "STAFF",
  "is_active": true
}
```

#### 실패

- `401 Unauthorized`: 인증 실패
- `404 Not Found`: 사용자를 찾을 수 없음

---

## 8. 회원 정보 수정 API

### 1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 회원 정보 수정 API |
| 설명 | 로그인한 사용자가 자신의 회원정보를 수정한다. |
| 엔드포인트 | `/api/v1/users/me` |
| 메서드 | `PATCH` |
| 인증 필요 여부 | Y |

### 2. 요청

#### Headers

| Key | Value | 설명 |
|---|---|---|
| Authorization | `Bearer <access_token>` | 로그인 사용자 인증 |
| Content-Type | `application/json` | 수정 정보 전달 |

#### 본문 필드

| 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| department | string | N | 변경할 부서 |
| phone_number | string | N | 변경할 전화번호 |

### 3. 응답

#### 성공

- `200 OK`

```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "홍길동",
  "department": "MEDICAL",
  "gender": "M",
  "phone_number": "01098765432",
  "role": "STAFF",
  "is_active": true
}
```

#### 실패

- `401 Unauthorized`: 인증 실패
- `409 Conflict`: 이미 사용 중인 전화번호
- `422 Unprocessable Entity`: 잘못된 입력값

### 4. 비고

일반 사용자는 이메일, 이름, 권한, 계정 활성화 여부를 직접 변경할 수 없다.

---

## 9. 비밀번호 변경 API

### 1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 비밀번호 변경 API |
| 설명 | 로그인한 사용자가 기존 비밀번호를 확인한 후 새 비밀번호로 변경한다. |
| 엔드포인트 | `/api/v1/users/me/password` |
| 메서드 | `PATCH` |
| 인증 필요 여부 | Y |

### 2. 요청

#### Headers

| Key | Value | 설명 |
|---|---|---|
| Authorization | `Bearer <access_token>` | 로그인 사용자 인증 |
| Content-Type | `application/json` | 비밀번호 변경 정보 전달 |

#### 본문 필드

| 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| current_password | string | Y | 기존 비밀번호 |
| new_password | string | Y | 새로운 비밀번호 |

### 3. 응답

#### 성공

- `204 No Content`

#### 실패

- `400 Bad Request`: 기존 비밀번호 불일치
- `401 Unauthorized`: 인증 실패
- `422 Unprocessable Entity`: 새 비밀번호 형식 오류

### 4. 비고

비밀번호 입력값은 화면에서 마스킹 처리하며, 새 비밀번호는 해시하여 저장한다.

---

## 10. 회원 탈퇴 API

### 1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 회원 탈퇴 API |
| 설명 | 로그인한 사용자가 자신의 계정을 탈퇴한다. |
| 엔드포인트 | `/api/v1/users/me` |
| 메서드 | `DELETE` |
| 인증 필요 여부 | Y |

### 2. 요청

#### Headers

| Key | Value | 설명 |
|---|---|---|
| Authorization | `Bearer <access_token>` | 로그인 사용자 인증 |

#### 본문 필드

| 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| - | - | N | 요청 본문을 사용하지 않음 |

#### 쿼리 파라미터

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| 없음 | - | N | 쿼리 파라미터를 사용하지 않음 |

### 3. 응답

#### 성공

- `204 No Content`

회원 탈퇴와 함께 리프레시 토큰 쿠키를 삭제한다.

#### 실패

- `401 Unauthorized`: 인증 실패
- `404 Not Found`: 사용자를 찾을 수 없음

### 4. 비고

회원 탈퇴 시 데이터베이스에서 해당 회원과 관련된 정보를 삭제한다.

---

## 11. 공통 오류 응답

### 401 Unauthorized

```json
{
  "detail": "인증이 필요합니다."
}
```

### 403 Forbidden

```json
{
  "detail": "해당 기능에 접근할 권한이 없습니다."
}
```

### 422 Unprocessable Entity

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

## 12. 공통 처리 기준

- 비밀번호는 원문으로 저장하지 않는다.
- 비밀번호와 비밀번호 해시는 응답에 포함하지 않는다.
- JWT payload에는 `user_id`만 저장한다.
- 액세스 토큰의 유효기간은 30분이다.
- 리프레시 토큰의 유효기간은 7일이다.
- 리프레시 토큰은 `HttpOnly` 쿠키로 전달한다.
- 관리자 전용 API는 `ADMIN` 권한을 확인한다.
- 모든 User API는 최대 3초 이내에 응답하도록 설계한다.