import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles

from app.apis.practice_apis import router
from app.apis.user_apis import router as user_router
from app.apis.patient import router as patient_router
from app.core.db.databases import Base, async_engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with async_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    await async_engine.dispose()

app = FastAPI(
    title="환자 관리 API",
    description="환자 정보 및 진료기록 관리 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(router)
app.include_router(user_router)
app.include_router(patient_router)

BASE_DIR = Path(__file__).resolve().parent.parent

# 만약 static, media, uploads 폴더가 존재하지 않으면 생성
if not (BASE_DIR / "static").exists():
    os.mkdir(BASE_DIR / "static")
if not (BASE_DIR / "media").exists():
    os.mkdir(BASE_DIR / "media")
if not (BASE_DIR / "uploads").exists():
    os.mkdir(BASE_DIR / "uploads")

# 'static' 폴더를 '/static' 경로로 마운트
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
# 'media' 폴더를 '/media' 경로로 마운트
app.mount("/media", StaticFiles(directory=BASE_DIR / "media"), name="media")
# 'uploads' 폴더를 '/uploads' 경로로 마운트
app.mount("/uploads", StaticFiles(directory=BASE_DIR / "uploads"), name="uploads")


@app.get(path="/healthcheck", status_code=200, include_in_schema=False)
async def healthcheck():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/{path:path}", include_in_schema=False)
async def catch_all(path: str):
    if path.startswith(("api/v1", "static/", "media/", "uploads/")):
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    return FileResponse(BASE_DIR / "static" / "index.html")

