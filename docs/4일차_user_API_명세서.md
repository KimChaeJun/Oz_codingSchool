# 4일차 User API 명세서

## 1. 문서 개요

- 기준 문서: `User 요구사항 정의서.md`
- API prefix: `/api/v1`
- 데이터 형식: `application/json`
- 인증 방식: `Authorization: Bearer <access_token>`
- 비밀번호 저장 방식: Argon2id 단방향 해시
- Access Token 만료: 30분
- Refresh Token 만료: 7일

이 문서는 회원가입, 로그인, 토큰 재발급, 로그아웃, 관리자 회원 관리,
마이페이지, 비밀번호 변경 및 회원 탈퇴 API의 요청·응답 계약을 정의한다.

## 2. 공통 정책

### 2.1 Enum

| 구분 | 허용 값 | 의미 |
| --- | --- | --- |
| `gender` | `M`, `F` | 남성, 여성 |
| `department` | `RESEARCH`, `MEDICAL`, `DEV` | 연구, 의료, 개발 |
| `role` | `PENDING`, `STAFF`, `ADMIN` | 대기자, 스태프, 관리자 |

회원가입으로 생성되는 계정의 초기 권한은 `PENDING`이다. 최초 `ADMIN` 계정은
운영자가 DB 또는 별도의 초기화 절차를 통해 지정한다.

### 2.2 입력 검증

| 필드 | 검증 규칙 |
| --- | --- |
| `email` | 유효한 이메일 형식, 최대 255자, 앞뒤 공백 제거 후 소문자로 저장, 중복 불가 |
| `password` | 8~64자, 영문 대문자·소문자·숫자·특수문자를 각각 1개 이상 포함 |
| `name` | 앞뒤 공백 제거, 2~20자 |
| `phone_number` | `010-1234-5678` 또는 `01012345678` 입력 허용, 숫자 11자리로 정규화, 중복 불가 |
| `user_ids` | 중복되지 않은 양의 정수 ID 1~100개 |

Pydantic 검증에 실패하면 FastAPI 기본 형식의 `422 Unprocessable Entity`를 반환한다.
정의되지 않은 요청 필드는 허용하지 않는다.

### 2.3 JWT 및 쿠키

- JWT 서명 알고리즘은 `HS256`을 사용한다.
- JWT에는 식별 정보로 `user_id`만 넣는다.
- `token_type`, `iat`, `exp`는 토큰 검증을 위한 메타데이터이며 이메일, 이름,
  권한 등의 개인정보는 넣지 않는다.
- Access Token은 JSON 응답으로 전달하고 클라이언트가 Bearer 헤더에 담아 사용한다.
- Refresh Token은 JavaScript에서 접근할 수 없는 `refresh_token` HttpOnly 쿠키로 전달한다.
- Refresh 쿠키 속성은 `HttpOnly`, `SameSite=Lax`, `Max-Age=604800`,
  `Path=/api/v1/auth`를 사용한다.
- HTTPS 운영 환경에서는 반드시 `Secure=true`로 설정한다.
- 권한은 JWT에 저장하지 않고 요청 시 DB에서 조회한다. 따라서 관리자가 변경한 권한이
  다음 요청부터 즉시 반영된다.

### 2.4 역할별 접근 범위

| 역할 | 접근 범위 |
| --- | --- |
| `PENDING` | 인증 API와 본인의 마이페이지 API만 접근 가능 |
| `STAFF` | 마이페이지 및 향후 X-Ray 관련 읽기·쓰기·수정 API 접근 가능 |
| `ADMIN` | 모든 User API와 시스템 관리 API 접근 가능 |

비활성 계정(`is_active=false`)은 로그인과 인증이 필요한 API를 사용할 수 없다.

### 2.5 공통 오류 응답

```json
{
  "detail": "오류 메시지"
}
```

| 상태 코드 | 발생 조건 |
| --- | --- |
| `400 Bad Request` | 수정할 필드가 없거나 현재 비밀번호와 새 비밀번호가 같은 경우 |
| `401 Unauthorized` | 로그인 실패, 토큰 누락·만료·위조·종류 불일치 |
| `403 Forbidden` | 비활성 계정 또는 권한 부족 |
| `404 Not Found` | 관리자 변경 대상 회원이 존재하지 않는 경우 |
| `409 Conflict` | 이메일 또는 휴대폰 번호 중복 |
| `422 Unprocessable Entity` | 요청 본문·경로·쿼리 검증 실패 |

## 3. API 목록

| 요구사항 | Method | Endpoint | 인증 | 설명 |
| --- | --- | --- | --- | --- |
| REQ-USER-001 | `POST` | `/api/v1/auth/signup` | 없음 | 회원가입 |
| REQ-USER-002 | `POST` | `/api/v1/auth/login` | 없음 | 로그인 및 토큰 발급 |
| NFR-USER-001 | `POST` | `/api/v1/auth/token/refresh` | Refresh Cookie | Access Token 재발급 |
| REQ-USER-003 | `POST` | `/api/v1/auth/logout` | 없음 | Refresh Cookie 삭제 |
| REQ-USER-004 | `GET` | `/api/v1/admin/users` | ADMIN | 회원 검색·필터·페이지 조회 |
| REQ-USER-005 | `PATCH` | `/api/v1/admin/users/roles` | ADMIN | 선택 회원 권한 일괄 변경 |
| REQ-USER-006 | `GET` | `/api/v1/users/me` | Bearer | 마이페이지 조회 |
| REQ-USER-007 | `PATCH` | `/api/v1/users/me` | Bearer | 내 부서·휴대폰 번호 수정 |
| REQ-USER-008 | `PATCH` | `/api/v1/users/me/password` | Bearer | 비밀번호 변경 |
| REQ-USER-009 | `DELETE` | `/api/v1/users/me` | Bearer | 회원 탈퇴 |

## 4. API 상세 명세

### 4.1 회원가입

`POST /api/v1/auth/signup`

Request Body

```json
{
  "email": "staff@example.com",
  "password": "Password1!",
  "name": "홍길동",
  "department": "MEDICAL",
  "gender": "M",
  "phone_number": "010-1234-5678"
}
```

Response: `201 Created`

```json
{
  "id": 1,
  "email": "staff@example.com",
  "name": "홍길동",
  "department": "MEDICAL",
  "gender": "M",
  "phone_number": "01012345678",
  "role": "PENDING",
  "is_active": true,
  "created_at": "2026-08-27T06:00:00"
}
```

예외: 이메일·휴대폰 번호 중복 `409`, 입력 검증 실패 `422`.
응답에 비밀번호 또는 비밀번호 해시는 포함하지 않는다.

### 4.2 로그인

`POST /api/v1/auth/login`

Request Body

```json
{
  "email": "staff@example.com",
  "password": "Password1!"
}
```

Response: `200 OK`

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 1800
}
```

응답과 함께 7일 만료의 `refresh_token` HttpOnly 쿠키를 설정한다.
이메일 또는 비밀번호가 일치하지 않는 경우 어느 항목이 틀렸는지 구분하지 않고
`401`을 반환한다. 비활성 계정은 `403`을 반환한다.

### 4.3 Access Token 재발급

`POST /api/v1/auth/token/refresh`

Request Cookie: `refresh_token=<jwt>`

Response: `200 OK`

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 1800
}
```

Refresh Token이 없거나 만료·위조·종류 불일치이면 `401`을 반환한다.
Refresh Token까지 만료되면 클라이언트는 로그인 화면으로 이동한다.

### 4.4 로그아웃

`POST /api/v1/auth/logout`

Response: `204 No Content`

`refresh_token` 쿠키를 즉시 삭제한다. 이미 쿠키가 없어도 동일하게 `204`를 반환해
멱등성을 보장한다. 발급된 Access Token은 최대 30분의 남은 유효기간 후 만료된다.

### 4.5 관리자 회원 목록 조회

`GET /api/v1/admin/users`

Query Parameters

| 이름 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `search` | `string?` | `null` | 이메일 또는 이름 부분 검색, 1~100자 |
| `department` | `Department?` | `null` | 부서 필터 |
| `page` | `integer` | `1` | 1 이상의 페이지 번호 |
| `size` | `integer` | `20` | 페이지 크기, 1~100 |

Response: `200 OK`

```json
{
  "items": [
    {
      "id": 1,
      "email": "staff@example.com",
      "name": "홍길동",
      "department": "MEDICAL",
      "gender": "M",
      "phone_number": "01012345678",
      "role": "PENDING",
      "is_active": true,
      "created_at": "2026-08-27T06:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

이메일 오름차순으로 정렬한다. 관리자가 아니면 `403`을 반환한다.

### 4.6 관리자 회원 권한 변경

`PATCH /api/v1/admin/users/roles`

Request Body

```json
{
  "user_ids": [2, 3],
  "role": "STAFF"
}
```

Response: `200 OK`

```json
{
  "updated_count": 2,
  "role": "STAFF"
}
```

요청한 ID 중 하나라도 존재하지 않으면 전체 변경을 수행하지 않고 누락된 ID와 함께
`404`를 반환한다. 관리자가 아니면 `403`을 반환한다.

### 4.7 마이페이지 조회

`GET /api/v1/users/me`

Response: `200 OK`

```json
{
  "id": 1,
  "email": "staff@example.com",
  "name": "홍길동",
  "department": "MEDICAL",
  "gender": "M",
  "phone_number": "01012345678",
  "role": "PENDING",
  "is_active": true,
  "created_at": "2026-08-27T06:00:00"
}
```

### 4.8 회원 정보 수정

`PATCH /api/v1/users/me`

Request Body

```json
{
  "department": "RESEARCH",
  "phone_number": "010-9876-5432"
}
```

두 필드는 모두 선택 사항이지만 최소 하나는 입력해야 한다. 입력한 필드만 수정한다.

Response: `200 OK` — 수정된 마이페이지 정보.

예외: 수정 필드 없음 `400`, 휴대폰 번호 중복 `409`.

### 4.9 비밀번호 변경

`PATCH /api/v1/users/me/password`

Request Body

```json
{
  "current_password": "Password1!",
  "new_password": "NewPassword2@"
}
```

Response: `204 No Content`

기존 비밀번호가 일치하지 않으면 `400`, 새 비밀번호가 기존 비밀번호와 같으면 `400`,
새 비밀번호 정책을 만족하지 않으면 `422`를 반환한다.

### 4.10 회원 탈퇴

`DELETE /api/v1/users/me`

Response: `204 No Content`

회원 레코드를 즉시 삭제하고 Refresh Cookie도 삭제한다. 현재 DB 외래키 정책에 따라
해당 회원이 업로드한 X-Ray의 `uploader_id`는 `NULL`로 변경되어 의료 기록은 보존된다.
삭제 이후 기존 토큰으로 사용자를 조회하면 `401`을 반환한다.

## 5. 비기능 요구사항 반영

### 5.1 비밀번호 보안

- 비밀번호는 Pydantic `SecretStr`로 받아 로그와 객체 표현에서 평문 노출을 줄인다.
- OpenAPI 스키마에서 비밀번호 필드는 `format: password`로 표시한다.
- DB에는 Argon2id 해시만 저장하며 응답 모델에서 `hashed_password`를 제외한다.
- 실제 화면의 마스킹과 보기 아이콘은 프론트엔드에서 구현한다.

### 5.2 성능

- 회원 목록은 최대 100개 단위로 페이지네이션한다.
- 이메일과 휴대폰 번호의 UNIQUE 인덱스를 중복 검사와 조회에 활용한다.
- 모든 DB 처리는 SQLAlchemy 비동기 세션을 사용한다.
- NFR의 3초 기준은 단위·통합 테스트 외에 운영 환경의 부하 테스트와 모니터링으로
  최종 확인해야 한다.

## 6. 요구사항 추적표

| 요구사항 ID | 반영 API/정책 |
| --- | --- |
| REQ-USER-001 | `POST /auth/signup` |
| REQ-USER-002 | `POST /auth/login` |
| NFR-USER-001 | JWT 정책, `POST /auth/token/refresh`, HttpOnly 쿠키 |
| REQ-USER-003 | `POST /auth/logout` |
| REQ-USER-004 | `GET /admin/users` 검색·부서 필터·페이지네이션 |
| REQ-USER-005 | `PATCH /admin/users/roles` |
| REQ-USER-006 | `GET /users/me` |
| REQ-USER-007 | `PATCH /users/me` |
| REQ-USER-008 | `PATCH /users/me/password` |
| REQ-USER-009 | `DELETE /users/me` |
| NFR-USER-002 | `SecretStr`, Argon2id, 응답 비밀번호 제외, 프론트엔드 책임 명시 |
| NFR-USER-003 | 비동기 DB, 인덱스, 페이지네이션, 운영 부하 테스트 기준 |

## 7. 참고자료

- [FastAPI 요청 본문](https://fastapi.tiangolo.com/ko/tutorial/body/)
- [FastAPI 쿼리 매개변수 모델](https://fastapi.tiangolo.com/ko/tutorial/query-param-models/)
- [FastAPI OAuth2, JWT 및 비밀번호 해싱](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [Pydantic Functional Validators](https://pydantic.dev/docs/validation/latest/api/pydantic/functional_validators/)
- [FastAPI에서 JWT로 사용자 회원가입/로그인 구현하기](https://suwani.tistory.com/188)
- [FastAPI 비밀번호 해싱하기(feat.argon2)](https://chaechae.life/blog/fastapi-password-hasing-with-agron2)
