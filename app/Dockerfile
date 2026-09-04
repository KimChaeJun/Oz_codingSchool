FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./

RUN pip install --no-cache-dir \
    alembic \
    asyncmy \
    cryptography \
    email-validator \
    "fastapi[standard]" \
    "pwdlib[argon2]" \
    pydantic-settings \
    pyjwt \
    "sqlalchemy[asyncio]" \
    uuid6 \
    redis

COPY app ./app
COPY static ./static
COPY alembic.ini ./

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]