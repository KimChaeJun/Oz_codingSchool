# 4일차 User API 설계

## 1. API 설계 개요

User 사용자 요구사항 정의서를 기반으로 회원가입, 로그인, 로그아웃, 인증 토큰 재발급, 회원 관리 및 마이페이지 관련 API를 설계한다.

### 1.1 인증 방식

- JWT(Json Web Token) 기반 인증/인가
- Access Token 만료 주기: 30분
- Refresh Token 만료 주기: 7일
- Refresh Token은 HttpOnly Cookie로 전달
- JWT Payload에는 최소 식별 정보인 `user_id`만 저장
- Access Token 만료 시 Refresh Token을 이용하여 Access Token을 재발급한다.
- Refresh Token 만료 시 재로그인이 필요하다.

### 1.2 사용자 권한

| 권한 | 설명 |
|------|------|
| PENDING | 대기자. 마이페이지 외 모든 서비스 접근 불가 |
| STAFF | 내부 직원. 흉부 X-Ray 관련 읽기, 쓰기, 수정 작업 가능 |
| ADMIN | 시스템 관리자. 모든 항목에 대한 데이터 접근 가능 |

### 1.3 부서

| 값 | 의미 |
|---|------|
| MEDICAL | 의료 |
| DEV | 개발 |
| RESEARCH | 연구 |

### 1.4 성별

| 값 | 의미 |
|---|------|
| M | 남성 |
| F | 여성 |

---

## 2. API 목록

| 번호 | 기능 | Method | Endpoint | 권한 |
|------|------|--------|----------|------|
| 1 | 회원가입 | POST | `/api/v1/users` | 비로그인 |
| 2 | 로그인 | POST | `/api/v1/auth/login` | 비로그인 |
| 3 | 로그아웃 | POST | `/api/v1/auth/logout` | 로그인 |
| 4 | Access Token 재발급 | POST | `/api/v1/auth/refresh` | Refresh Token 필요 |
| 5 | 회원 목록 조회 | GET | `/api/v1/users` | ADMIN |
| 6 | 회원 권한 변경 | PATCH | `/api/v1/users/{user_id}/role` | ADMIN |
| 7 | 마이페이지 조회 | GET | `/api/v1/users/me` | 로그인 |
| 8 | 회원 정보 수정 | PATCH | `/api/v1/users/me` | 로그인 |
| 9 | 비밀번호 변경 | PATCH | `/api/v1/users/me/password` | 로그인 |
| 10 | 회원 탈퇴 | DELETE | `/api/v1/users/me` | 로그인 |

---

## 3. API 상세 명세

### 3.1 회원가입

#### 기본 정보

- 기능: 회원가입
- 요구사항 ID: REQ-USER-001
- Method: POST
- Endpoint: `/api/v1/users`
- 인증: 불필요

#### Request Body

```json
{
  "email": "user@example.com",
  "password": "Password1234!",
  "name": "홍길동",
  "department": "MEDICAL",
  "gender": "M",
  "phone_number": "010-1234-5678"
}
```

#### Request 항목

| 항목 | 타입 | 필수 | 설명 |
|------|------|------|------|
| email | string | Y | 사용자 이메일 |
| password | string | Y | 비밀번호 |
| name | string | Y | 사용자 이름 |
| department | string | Y | MEDICAL, DEV, RESEARCH |
| gender | string | Y | M, F |
| phone_number | string | Y | 휴대폰 번호 |

#### 처리

1. 이메일 중복 여부를 확인한다.
2. 휴대폰 번호 중복 여부를 확인한다.
3. 입력된 비밀번호를 해싱한다.
4. 사용자 정보를 저장한다.
5. 초기 권한은 `PENDING`으로 설정한다.
6. 계정 활성화 상태는 활성 상태로 설정한다.

#### Response

**201 Created**

```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "홍길동",
  "department": "MEDICAL",
  "gender": "M",
  "phone_number": "010-1234-5678",
  "role": "PENDING",
  "is_active": true
}
```

#### 주요 상태 코드

| 상태 코드 | 설명 |
|----------|------|
| 201 | 회원가입 성공 |
| 400 | 잘못된 요청 |
| 409 | 이메일 또는 휴대폰 번호 중복 |
| 422 | 필수 값 누락 또는 입력 형식 오류 |

---

### 3.2 로그인

#### 기본 정보

- 기능: 로그인
- 요구사항 ID: REQ-USER-002
- Method: POST
- Endpoint: `/api/v1/auth/login`
- 인증: 불필요

#### Request Body

```json
{
  "email": "user@example.com",
  "password": "Password1234!"
}
```

#### Request 항목

| 항목 | 타입 | 필수 | 설명 |
|------|------|------|------|
| email | string | Y | 가입한 이메일 |
| password | string | Y | 비밀번호 |

#### 처리

1. 이메일로 사용자를 조회한다.
2. 입력한 비밀번호와 저장된 해시 비밀번호를 비교한다.
3. 로그인 가능한 계정인지 확인한다.
4. Access Token을 발급한다.
5. Refresh Token을 발급한다.
6. Refresh Token은 HttpOnly Cookie로 전달한다.

#### Response

**200 OK**

```json
{
  "access_token": "access-token",
  "token_type": "bearer"
}
```

Refresh Token은 HttpOnly Cookie로 전달한다.

#### 주요 상태 코드

| 상태 코드 | 설명 |
|----------|------|
| 200 | 로그인 성공 |
| 401 | 이메일 또는 비밀번호가 올바르지 않음 |
| 403 | 비활성화 또는 접근 제한 계정 |

---

### 3.3 로그아웃

#### 기본 정보

- 기능: 로그아웃
- 요구사항 ID: REQ-USER-003
- Method: POST
- Endpoint: `/api/v1/auth/logout`
- 인증: 로그인 필요

#### 처리

Refresh Token이 저장된 HttpOnly Cookie를 삭제한다.

#### Response

**204 No Content**

#### 주요 상태 코드

| 상태 코드 | 설명 |
|----------|------|
| 204 | 로그아웃 성공 |
| 401 | 인증되지 않은 사용자 |

---

### 3.4 Access Token 재발급

#### 기본 정보

- 기능: Access Token 재발급
- 요구사항 ID: NFR-USER-001
- Method: POST
- Endpoint: `/api/v1/auth/refresh`
- 인증: 유효한 Refresh Token 필요

#### Request

별도의 Request Body는 사용하지 않는다. HttpOnly Cookie에 저장된 Refresh Token을 사용한다.

#### 처리

1. HttpOnly Cookie에서 Refresh Token을 확인한다.
2. Refresh Token의 유효성을 검증한다.
3. Refresh Token의 `user_id`를 확인한다.
4. 새로운 Access Token을 발급한다.
5. 새로운 Access Token을 응답한다.

#### Response

**200 OK**

```json
{
  "access_token": "new-access-token",
  "token_type": "bearer"
}
```

#### 주요 상태 코드

| 상태 코드 | 설명 |
|----------|------|
| 200 | Access Token 재발급 성공 |
| 401 | Refresh Token이 없거나 유효하지 않음 |

---

### 3.5 회원 목록 조회

#### 기본 정보

- 기능: 회원 목록 조회
- 요구사항 ID: REQ-USER-004
- Method: GET
- Endpoint: `/api/v1/users`
- 인증: ADMIN 권한 필요

#### Query Parameters

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| search | string | N | 이메일 또는 이름 검색 |
| department | string | N | 부서별 필터링 |

#### Request 예시

```text
GET /api/v1/users?search=홍길동&department=MEDICAL
```

#### 처리

- 모든 회원을 조회할 수 있다.
- `search`가 입력되면 이메일 또는 이름을 기준으로 검색한다.
- `department`가 입력되면 해당 부서의 회원만 조회한다.
- 관리자만 해당 API를 사용할 수 있다.

#### Response

**200 OK**

```json
[
  {
    "id": 1,
    "email": "user@example.com",
    "name": "홍길동",
    "department": "MEDICAL",
    "gender": "M",
    "phone_number": "010-1234-5678",
    "role": "STAFF",
    "is_active": true
  }
]
```

#### Response 항목

| 항목 | 타입 | 설명 |
|------|------|------|
| id | integer | 회원 ID |
| email | string | 회원 이메일 |
| name | string | 회원 이름 |
| department | string | 부서 |
| gender | string | 성별 (M/F) |
| phone_number | string | 휴대폰 번호 |
| role | string | 권한 (PENDING/STAFF/ADMIN) |
| is_active | boolean | 계정 활성화 여부 |

#### 주요 상태 코드

| 상태 코드 | 설명 |
|----------|------|
| 200 | 조회 성공 |
| 401 | 인증되지 않은 사용자 |
| 403 | ADMIN 권한이 없음 |

---

### 3.6 회원 권한 변경

#### 기본 정보

- 기능: 회원 권한 변경
- 요구사항 ID: REQ-USER-005
- Method: PATCH
- Endpoint: `/api/v1/users/{user_id}/role`
- 인증: ADMIN 권한 필요

#### Path Parameter

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| user_id | integer | Y | 권한을 변경할 회원의 ID |

#### Request Body

```json
{
  "role": "STAFF"
}
```

#### Request 항목

| 항목 | 타입 | 필수 | 설명 |
|------|------|------|------|
| role | string | Y | PENDING, STAFF, ADMIN |

#### 처리

1. 관리자 권한을 확인한다.
2. 대상 회원을 조회한다.
3. 요청된 권한으로 회원의 권한을 변경한다.

#### Response

**200 OK**

```json
{
  "id": 1,
  "role": "STAFF"
}
```

#### 주요 상태 코드

| 상태 코드 | 설명 |
|----------|------|
| 200 | 권한 변경 성공 |
| 401 | 인증되지 않은 사용자 |
| 403 | ADMIN 권한이 없음 |
| 404 | 회원을 찾을 수 없음 |

---

### 3.7 마이페이지 조회

#### 기본 정보

- 기능: 마이페이지 조회
- 요구사항 ID: REQ-USER-006
- Method: GET
- Endpoint: `/api/v1/users/me`
- 인증: 로그인 필요

#### Response

**200 OK**

```json
{
  "id": 1,
  "name": "홍길동",
  "email": "user@example.com",
  "department": "MEDICAL",
  "gender": "M",
  "phone_number": "010-1234-5678",
  "role": "STAFF"
}
```

#### Response 항목

| 항목 | 타입 | 설명 |
|------|------|------|
| id | integer | 사용자 ID |
| name | string | 사용자 이름 |
| email | string | 사용자 이메일 |
| department | string | 부서 (MEDICAL/DEV/RESEARCH) |
| gender | string | 성별 (M/F) |
| phone_number | string | 휴대폰 번호 |
| role | string | 권한 (PENDING/STAFF/ADMIN) |

#### 주요 상태 코드

| 상태 코드 | 설명 |
|----------|------|
| 200 | 조회 성공 |
| 401 | 인증되지 않은 사용자 |

---

### 3.8 회원 정보 수정

#### 기본 정보

- 기능: 회원 정보 수정
- 요구사항 ID: REQ-USER-007
- Method: PATCH
- Endpoint: `/api/v1/users/me`
- 인증: 로그인 필요

#### Request Body

```json
{
  "department": "DEV",
  "phone_number": "010-9876-5432"
}
```

#### Request 항목

| 항목 | 타입 | 필수 | 설명 |
|------|------|------|------|
| department | string | N | MEDICAL, DEV, RESEARCH |
| phone_number | string | N | 휴대폰 번호 |

※ Partial Update 방식으로 필요한 항목만 전달한다.

#### Response

**200 OK**

```json
{
  "name": "홍길동",
  "email": "user@example.com",
  "department": "DEV",
  "gender": "M",
  "phone_number": "010-9876-5432",
  "role": "STAFF"
}
```

#### 주요 상태 코드

| 상태 코드 | 설명 |
|----------|------|
| 200 | 정보 수정 성공 |
| 401 | 인증되지 않은 사용자 |
| 409 | 휴대폰 번호 중복 |
| 422 | 입력 형식 오류 |

---

### 3.9 비밀번호 변경

#### 기본 정보

- 기능: 비밀번호 변경
- 요구사항 ID: REQ-USER-008
- Method: PATCH
- Endpoint: `/api/v1/users/me/password`
- 인증: 로그인 필요

#### Request Body

```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewPassword123!"
}
```

#### Request 항목

| 항목 | 타입 | 필수 | 설명 |
|------|------|------|------|
| current_password | string | Y | 기존 비밀번호 |
| new_password | string | Y | 새로운 비밀번호 |

#### 처리

1. 로그인한 사용자를 확인한다.
2. 기존 비밀번호와 입력된 비밀번호가 일치하는지 검증한다.
3. 새로운 비밀번호를 해싱한다.
4. 해싱된 비밀번호를 저장한다.

#### Response

**204 No Content**

#### 주요 상태 코드

| 상태 코드 | 설명 |
|----------|------|
| 204 | 비밀번호 변경 성공 |
| 401 | 인증되지 않은 사용자 또는 기존 비밀번호 불일치 |
| 422 | 입력 형식 오류 |

---

### 3.10 회원 탈퇴

#### 기본 정보

- 기능: 회원 탈퇴
- 요구사항 ID: REQ-USER-009
- Method: DELETE
- Endpoint: `/api/v1/users/me`
- 인증: 로그인 필요

#### 처리

1. 로그인한 사용자를 확인한다.
2. 해당 회원과 관련된 데이터를 확인한다.
3. 회원 및 관련 정보를 데이터베이스에서 삭제한다.
4. 인증 관련 쿠키를 삭제한다.

#### Response

**204 No Content**

#### 주요 상태 코드

| 상태 코드 | 설명 |
|----------|------|
| 204 | 회원 탈퇴 성공 |
| 401 | 인증되지 않은 사용자 |

---

## 4. 표준 에러 응답

### 400 Bad Request

```json
{
  "detail": "잘못된 요청입니다."
}
```

### 401 Unauthorized

```json
{
  "detail": "인증이 필요합니다."
}
```

### 403 Forbidden

```json
{
  "detail": "해당 작업에 필요한 권한이 없습니다."
}
```

### 404 Not Found

```json
{
  "detail": "요청한 리소스를 찾을 수 없습니다."
}
```

### 409 Conflict

```json
{
  "detail": "이메일 또는 휴대폰 번호가 이미 존재합니다."
}
```

### 422 Unprocessable Entity

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "Invalid email format",
      "type": "value_error"
    }
  ]
}
```

---

## 5. 공통 정책

### 5.1 비밀번호 보안

- 비밀번호는 평문으로 저장하지 않는다.
- 서버에서 안전한 해싱 알고리즘을 사용하여 저장한다.
- 비밀번호 입력 UI는 마스킹 처리한다.
- 비밀번호 보기 기능은 클라이언트에서 처리한다.

### 5.2 JWT 보안

- Access Token 만료 주기: 30분
- Refresh Token 만료 주기: 7일
- Refresh Token은 HttpOnly Cookie로 전달한다.
- JWT Payload에는 최소 식별 정보인 `user_id`만 저장한다.
- 로그인 필요한 API 요청은 Authorization 헤더에 `Bearer {access_token}` 형식으로 Access Token을 전달한다.

### 5.3 API 성능

- 모든 User API는 최대 3초 이내에 로직을 처리하고 응답하도록 한다.

### 5.4 권한

- 회원가입 및 로그인은 인증 없이 접근할 수 있다.
- 회원 목록 조회 및 회원 권한 변경은 ADMIN만 접근할 수 있다.
- 마이페이지 관련 API는 로그인한 사용자 본인만 접근할 수 있다.
- JWT를 통해 사용자 인증 및 API 접근 권한을 확인한다.

### 5.5 요청 Headers

로그인이 필요한 API는 다음 Authorization Header를 사용한다.

| Header | 필수 | 설명 |
|--------|------|------|
| Authorization | Y | `Bearer {access_token}` |

요청 본문이 JSON인 POST/PATCH API는 다음 Header를 사용한다.

| Header | 필수 | 설명 |
|--------|------|------|
| Content-Type | Y | `application/json` |

### 5.6 검증 규칙

| 항목 | 규칙 | 설명 |
|------|------|------|
| email | 이메일 형식 | 유효한 이메일 형식 |
| password | 문자열 | 비밀번호 입력값 |
| phone_number | 형식 검증 | 휴대폰 번호 형식 |
| name | 문자열 | 사용자 이름 |
| department | Enum | MEDICAL, DEV, RESEARCH만 허용 |
| gender | Enum | M, F만 허용 |
| role | Enum | PENDING, STAFF, ADMIN만 허용 |
