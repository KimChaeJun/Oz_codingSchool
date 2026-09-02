# Base image 선택 (pyproject.toml의 requires-python >= 3.13 준수)
FROM python:3.13-slim

# 공식 uv 배포 이미지에서 바이너리만 가져와 설치 (버전 고정)
COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /uvx /usr/local/bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# 컨테이너 내부 작업 경로 = 프로젝트(레포) 루트
WORKDIR /app

# asyncmy 등 C 확장 패키지 빌드에 필요한 컴파일러 설치 (uv sync 전에 필요)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 의존성 정의 파일만 먼저 복사 (레이어 캐시: 앱 코드만 바뀌면 이 설치 단계는 재사용됨)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# 프로젝트 전체 복사 (app 패키지, static/, media/, alembic 등 포함)
COPY . .

EXPOSE 8000

# docker-compose 없이 단독 실행할 때 사용되는 기본 명령 (--reload는 compose 쪽에서 적용)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
