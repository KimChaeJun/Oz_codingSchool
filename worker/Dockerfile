FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir \
    redis \
    torch \
    torchvision \
    pillow

COPY worker ./worker

CMD ["python", "-m", "worker.main"]