from fastapi import APIRouter, Path, Query, Body, HTTPException
from pydantic import BaseModel


router = APIRouter()

# 샘플 데이터
all_items = [
    {"id": 1, "name": "apple", "price": 100},
    {"id": 2, "name": "banana", "price": 200},
    {"id": 3, "name": "cherry", "price": 300},
]

# 응답 형식 정의
class ItemResponse(BaseModel):
    id: int
    name: str
    price: int

# GET /items - 전체 상품 조회
@router.get(
    "/items",
    summary="전체 상품 조회 API",
    response_model=list[ItemResponse]
)
def get_all_items_handler():
    """모든 상품을 조회합니다."""
    return all_items


# GET /items/search - 상품 검색
@router.get(
    "/items/search",
    summary="상품 검색 API",
    response_model=list[ItemResponse],
)
def search_item_handler(
    query: str = Query(..., min_length=2)  # 최소 2글자 이상
):
    """상품 이름으로 검색합니다."""
    result = []
    for item in all_items:
        if query in item["name"]:
            result.append(item)
    return result


# GET /items/{item_id} - 단일 상품 조회
@router.get(
    "/items/{item_id}",
    summary="단일 상품 조회 API",
    response_model=ItemResponse
)
def get_item_handler(
    item_id: int = Path(..., ge=1)  # 1 이상인지 검사
):
    """특정 상품을 조회합니다."""
    for item in all_items:
        if item["id"] == item_id:
            return item

    raise HTTPException(
        status_code=404,
        detail="아이템을 찾을 수 없습니다."
    )


# 상품 등록 요청 모델
class ItemRegisterRequest(BaseModel):
    name: str
    price: int


# POST /items - 상품 등록
@router.post(
    "/items",
    summary="상품 등록 API",
    status_code=201,  # 새로운 리소스 생성
    response_model=ItemResponse,
)
def register_item_handler(
    body: ItemRegisterRequest
):
    """새로운 상품을 등록합니다."""
    new_item = {
        "id": len(all_items) + 1,  # 기본키는 서버에서 발급
        "name": body.name,
        "price": body.price,
    }
    all_items.append(new_item)
    return new_item


# 상품 수정 요청 모델
class ItemUpdateRequest(BaseModel):
    name: str | None = None
    price: int | None = None


# PATCH /items/{item_id} - 상품 부분 수정
@router.patch(
    "/items/{item_id}",
    summary="상품 수정 API",
    response_model=ItemResponse,
)
def update_item_handler(
    item_id: int = Path(..., ge=1),
    body: ItemUpdateRequest = Body(...),
):
    """기존 상품을 부분 수정합니다."""
    for item in all_items:
        if item["id"] == item_id:
            if body.name:
                item["name"] = body.name
            if body.price:
                item["price"] = body.price
            return item

    raise HTTPException(
        status_code=404,
        detail="아이템을 찾을 수 없습니다."
    )