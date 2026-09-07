import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_ROOT = BASE_DIR / "media"
XRAY_SUBDIR = "xray"

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
CHUNK_SIZE = 1024 * 1024  # 1MB

FILE_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}


def _has_valid_signature(content_type: str, header: bytes) -> bool:
    signatures = FILE_SIGNATURES.get(content_type, ())
    return any(header.startswith(signature) for signature in signatures)


async def save_xray_image(file: UploadFile) -> str:
    extension = ALLOWED_CONTENT_TYPES.get(file.content_type or "")
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="X-Ray 이미지는 JPEG 또는 PNG 형식만 업로드할 수 있습니다.",
        )

    chunks: list[bytes] = []
    header = b""
    total_size = 0
    while chunk := await file.read(CHUNK_SIZE):
        total_size += len(chunk)
        if total_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="X-Ray 이미지는 10MB를 초과할 수 없습니다.",
            )
        if not header:
            header = chunk[:16]
        chunks.append(chunk)

    if total_size == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="빈 파일은 업로드할 수 없습니다.",
        )

    if not _has_valid_signature(file.content_type, header):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="파일 내용이 선언된 이미지 형식과 일치하지 않습니다.",
        )

    directory = MEDIA_ROOT / XRAY_SUBDIR
    directory.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{extension}"
    destination = directory / filename

    try:
        await run_in_threadpool(destination.write_bytes, b"".join(chunks))
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    return f"/media/{XRAY_SUBDIR}/{filename}"


def delete_xray_image(image_url: str) -> None:
    relative_path = image_url.removeprefix("/media/")
    file_path = MEDIA_ROOT / relative_path
    file_path.unlink(missing_ok=True)


def resolve_media_path(image_url: str) -> Path:
    """DB에 저장된 공개 media URL을 실제 파일 경로로 변환한다.

    image_url을 그대로 이어붙이면 "../"가 섞여 있을 때 MEDIA_ROOT
    바깥으로 벗어나는 경로 조작이 가능해지므로, 최종 경로가 MEDIA_ROOT
    하위인지 검증한 뒤에만 반환한다.
    """
    if not image_url.startswith("/media/"):
        raise ValueError(f"지원하지 않는 media 경로입니다: {image_url}")

    media_root = MEDIA_ROOT.resolve()
    relative_path = image_url.removeprefix("/media/")
    file_path = (media_root / relative_path).resolve()

    if not file_path.is_relative_to(media_root):
        raise ValueError(f"media 저장소 범위를 벗어난 경로입니다: {image_url}")

    return file_path
