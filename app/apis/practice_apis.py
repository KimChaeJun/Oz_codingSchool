import re
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Response, status
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints


router = APIRouter(prefix="/practice_api", tags=["practice-api"])

user_list = [
    {
        "id": 1,
        "name": "홍길동",
        "age": 24,
        "email": "gildong24@example.com",
        "password": "Password1234!!",
    },
    {
        "id": 2,
        "name": "장문복",
        "age": 21,
        "email": "moonluck12@example.com",
        "password": "Check1321!",
    },
    {
        "id": 3,
        "name": "임우진",
        "age": 31,
        "email": "limousine33@example.com",
        "password": "lwsPAssword12@",
    },
]

EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)


def validate_email(value: str) -> str:
    value = value.strip()
    if not EMAIL_PATTERN.fullmatch(value):
        raise ValueError("올바른 이메일 형식이 아닙니다.")
    return value


def validate_password(value: str) -> str:
    if not re.search(r"[a-z]", value):
        raise ValueError("비밀번호에는 소문자가 1개 이상 포함되어야 합니다.")
    if not re.search(r"[A-Z]", value):
        raise ValueError("비밀번호에는 대문자가 1개 이상 포함되어야 합니다.")
    if not re.search(r"[^A-Za-z0-9\s]", value):
        raise ValueError("비밀번호에는 특수문자가 1개 이상 포함되어야 합니다.")
    return value


Name = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=10),
]
Age = Annotated[int, Field(ge=14)]
Email = Annotated[str, Field(max_length=30), AfterValidator(validate_email)]
Password = Annotated[
    str,
    Field(min_length=8, max_length=20),
    AfterValidator(validate_password),
]


class UserResponse(BaseModel):
    id: int
    name: str
    age: int
    email: str


class UserCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    age: Age
    email: Email
    password: Password


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age: Age | None = None
    email: Email | None = None
    password: Password | None = None


def find_user(user_id: int) -> dict:
    for user in user_list:
        if user["id"] == user_id:
            return user
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="회원을 찾을 수 없습니다.",
    )


def email_is_already_registered(email: str, excluded_user_id: int | None = None) -> bool:
    return any(
        user["id"] != excluded_user_id
        and user["email"].casefold() == email.casefold()
        for user in user_list
    )


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="모든 회원 조회",
)
def get_users() -> list[dict]:
    return user_list


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="특정 회원 조회",
)
def get_user(user_id: Annotated[int, Path(description="조회할 회원의 ID")]) -> dict:
    return find_user(user_id)


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원 등록",
)
def create_user(body: UserCreateRequest) -> dict:
    if email_is_already_registered(body.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다.",
        )

    new_user = {
        "id": max((user["id"] for user in user_list), default=0) + 1,
        **body.model_dump(),
    }
    user_list.append(new_user)
    return new_user


@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="회원 정보 수정",
)
def update_user(
    user_id: Annotated[int, Path(description="수정할 회원의 ID")],
    body: UserUpdateRequest,
) -> dict:
    user = find_user(user_id)
    updates = body.model_dump(exclude_unset=True, exclude_none=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수정할 항목을 하나 이상 입력해야 합니다.",
        )

    if "email" in updates and email_is_already_registered(
        updates["email"], excluded_user_id=user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다.",
        )

    user.update(updates)
    return user


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="회원 삭제",
)
def delete_user(
    user_id: Annotated[int, Path(description="삭제할 회원의 ID")],
) -> Response:
    user = find_user(user_id)
    user_list.remove(user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
