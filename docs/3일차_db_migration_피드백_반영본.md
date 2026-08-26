# 3일차 - 데이터베이스 마이그레이션

## 개요

SQLAlchemy ORM으로 정의된 데이터베이스 모델을 Alembic을 사용하여 실제 MySQL 데이터베이스 스키마로 변환하는 과정을 수행했습니다.

---

## 1. 데이터베이스 선택

**선택된 데이터베이스: MySQL 8.0+**

### 선택 이유
- 프로젝트 기본 설정이 MySQL로 구성됨 (`app/core/config.py`)
- 팀 환경에서 실무적 경험
- 확장 가능한 대규모 프로젝트에 적합

### 데이터베이스 연결 정보
```
Host: localhost
Port: 3306
Database: ai_health
Username: root
Password: password1234
```

---

## 2. SQLAlchemy ORM 모델

### 작성된 모델 파일

| 파일명 | 모델 클래스 | 테이블명 | 설명 |
|--------|-----------|---------|------|
| `app/models/user.py` | User | users | 시스템 사용자 정보 |
| `app/models/patient.py` | Patient | patients | 환자 정보 |
| `app/models/medical_record.py` | MedicalRecord | medical_records | 진료 기록 |
| `app/models/xray_image.py` | XrayImage | xray_images | X-ray 이미지 |
| `app/models/ai_analysis_result.py` | AiAnalysisResult | ai_analysis_results | AI 분석 결과 |

### 모델 구조

**Mixin 클래스 활용:**
- `UUIDMixin`: UUID 기반 기본 키 (uuid7)
- `TimestampMixin`: created_at, updated_at 자동 기록
- `SoftDeleteMixin`: 소프트 삭제 기능

**Enum 활용:**
- `GenderEnum`: M (남), F (여)
- `RoleEnum`: PENDING, STAFF, ADMIN
- `DepartmentEnum`: MEDICAL, DEV, RESEARCH

---

## 3. Alembic 마이그레이션

### 마이그레이션 파일 생성

```bash
alembic revision --autogenerate -m "Add initial schema"
```

**생성된 파일:**
- `alembic/versions/2a635f4b60e5_add_initial_schema.py`

### 마이그레이션 내용

Alembic이 다음 5개 테이블을 감지하고 마이그레이션 코드 자동 생성:
- `patients` 테이블
- `users` 테이블
- `medical_records` 테이블
- `ai_analysis_results` 테이블
- `xray_images` 테이블

### 마이그레이션 적용

```bash
alembic upgrade head
```

**실행 결과:**
```
INFO  [alembic.runtime.migration] Context impl MySQLImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 2a635f4b60e5, Add initial schema
```

---

## 4. 생성된 데이터베이스 스키마

### 테이블 목록

```sql
USE ai_health;
SHOW TABLES;
```

**결과:**
| Tables_in_ai_health |
|-------------------|
| ai_analysis_results |
| alembic_version |
| medical_records |
| patients |
| users |
| xray_images |

### 테이블 상세 정보

#### users 테이블
- **용도:** 시스템 사용자 (의료진, 개발팀, 연구진)
- **주요 필드:** 
  - uuid (PK): UUID 기반 기본 키
  - email: 고유 이메일
  - hashed_password: 해시된 비밀번호
  - name: 사용자 이름
  - phone_number: 고유 전화번호
  - gender: 성별 (enum)
  - department: 부서 (enum)
  - role: 권한 역할 (enum)
  - is_active: 계정 활성화 여부
  - created_at, updated_at: 타임스탐프

#### patients 테이블
- **용도:** 환자 기본 정보
- **주요 필드:**
  - id (PK): BigInteger 기본 키
  - name: 환자 성명
  - age: 환자 나이
  - gender: 성별 (선택사항)
  - phone: 환자 연락처
  - created_at, updated_at: 타임스탐프

#### medical_records 테이블
- **용도:** 진료 기록
- **주요 필드:**
  - id (PK): BigInteger 기본 키
  - patient_id (FK): 환자 정보 참조
  - chart_number: 고유 차트 번호
  - symptoms: 환자 증상 기록
  - created_at, updated_at: 타임스탐프
- **관계:** patients (1:N)

#### xray_images 테이블
- **용도:** X-ray 이미지 저장
- **주요 필드:**
  - id (PK): BigInteger 기본 키
  - record_id (FK): 진료 기록 참조
  - uploader_id (FK): 업로더 사용자 참조
  - image_url: 이미지 URL
  - shooting_datetime: X-ray 촬영 일시
  - created_at: 등록 일시
- **관계:** medical_records (1:N), users (N:1)

#### ai_analysis_results 테이블
- **용도:** AI 분석 결과
- **주요 필드:**
  - id (PK): BigInteger 기본 키
  - record_id (FK): 진료 기록 참조
  - is_pneumonia: 폐렴 진단 여부
  - confidence: AI 예측 신뢰도 (0~100)
  - heatmap_url: 히트맵 이미지 URL
  - ai_model: 사용된 AI 모델명
  - created_at, updated_at: 타임스탐프
- **관계:** medical_records (1:N)

---

## 5. DBeaver를 통한 스키마 확인

### DBeaver 연결 설정

**MySQL 연결:**
- Host: localhost
- Port: 3306
- Database: ai_health
- Username: root
- Password: ****

### 생성된 테이블 확인

DBeaver의 Database Navigator에서 `ai_health` 데이터베이스 내 모든 테이블 확인:

```
ai_health
├── Tables
│   ├── ai_analysis_results (3K)
│   ├── alembic_version (16K)
│   ├── medical_records (48K)
│   ├── patients (16K)
│   ├── users (48K)
│   └── xray_images (48K)
├── Views
├── Indexes
├── Procedures
├── Triggers
└── Events
```

### DBeaver 스크린샷

![DB 스키마 확인](./DB%20스키마.png)

---

## 6. 마이그레이션 프로세스 정리

### 단계별 수행 과정

1. **모델 정의** ✅
   - SQLAlchemy ORM 모델 5개 작성
   - app/models/ 디렉토리에 각 테이블별 파일 생성

2. **마이그레이션 파일 생성** ✅
   ```bash
   alembic revision --autogenerate -m "Add initial schema"
   ```

3. **마이그레이션 파일 검토** ✅
   - `alembic/versions/2a635f4b60e5_add_initial_schema.py` 확인
   - 모든 테이블 생성 쿼리 포함

4. **마이그레이션 적용** ✅
   ```bash
   alembic upgrade head
   ```

5. **스키마 검증** ✅
   - MySQL: `SHOW TABLES;`로 테이블 확인
   - DBeaver: GUI로 스키마 시각적 확인

---

## 7. 향후 마이그레이션 방법

### 새로운 모델 추가 시

```bash
# 1. 모델 파일 생성 (예: app/models/new_model.py)

# 2. app/models/__init__.py에 import 추가
from app.models.new_model import NewModel

# 3. app/main.py에 import 추가 (Alembic 감지용)
from app.models import NewModel

# 4. 마이그레이션 생성
alembic revision --autogenerate -m "Add new_model table"

# 5. 마이그레이션 확인 및 적용
alembic upgrade head
```

### 기존 모델 수정 시

```bash
# 1. 모델 파일 수정

# 2. 마이그레이션 자동 생성
alembic revision --autogenerate -m "Modify model_name"

# 3. 생성된 마이그레이션 파일 검토 (필요시 수정)

# 4. 적용
alembic upgrade head
```

---

## 8. 참고사항

### 사용 기술 스택
- **ORM**: SQLAlchemy 2.0+
- **마이그레이션**: Alembic
- **데이터베이스**: MySQL 8.0+
- **비동기 드라이버**: asyncmy
- **DB 클라이언트**: DBeaver Community

### Foreign Key 관계
- `medical_records.patient_id` → `patients.id` (CASCADE DELETE)
- `xray_images.record_id` → `medical_records.id` (CASCADE DELETE)
- `xray_images.uploader_id` → `users.id` (SET NULL DELETE)
- `ai_analysis_results.record_id` → `medical_records.id` (CASCADE DELETE)

### 테이블 크기
- 초기 상태이므로 모든 테이블이 매우 작음 (3-48K)
- 실제 운영 환경에서는 데이터 증가에 따라 증가

---

