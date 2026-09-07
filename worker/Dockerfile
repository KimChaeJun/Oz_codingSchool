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

# 의존성 정의 파일만 먼저 복사 (레이어 캐시: worker 코드만 바뀌면 이 설치 단계는 재사용됨)
# --extra ai: torch/torchvision/pillow만 설치, app extra(fastapi/sqlalchemy 등)는 제외해 이미지 용량을 줄임
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev --extra ai

# 프로젝트 전체 복사 (worker 패키지, shared/, worker/models/*.pth 등 포함)
COPY . .

CMD ["python", "-m", "worker.main"]
