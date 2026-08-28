import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_ROOT = BASE_DIR / "media"
XRAY_SUBDIR = "xray"

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


async def save_xray_image(file: UploadFile) -> str:
    extension = ALLOWED_CONTENT_TYPES.get(file.content_type or "")
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="X-Ray 이미지는 JPEG 또는 PNG 형식만 업로드할 수 있습니다.",
        )

    directory = MEDIA_ROOT / XRAY_SUBDIR
    directory.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{extension}"
    destination = directory / filename

    content = await file.read()
    destination.write_bytes(content)

    return f"/media/{XRAY_SUBDIR}/{filename}"


def delete_xray_image(image_url: str) -> None:
    relative_path = image_url.removeprefix("/media/")
    file_path = MEDIA_ROOT / relative_path
    file_path.unlink(missing_ok=True)
