FROM python:3.13-slim

WORKDIR /workspace

COPY pyproject.toml uv.lock ./

RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev

COPY . .

ENV PATH="/workspace/.venv/bin:$PATH" \
    PYTHONPATH="/workspace"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
