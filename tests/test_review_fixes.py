"""
코드 리뷰에서 확인된 인증, 사용자 검증 및 예외 처리 항목에 대한 회귀 테스트.
DB 연결 없이 주요 로직의 동작을 검증한다.
"""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_refresh_token,
)
from app.schemas.user import UserCreateRequest, UserUpdateRequest
from app.services import user as user_service


class FakeUser:
    def __init__(self, id: int = 1, is_active: bool = True):
        self.id = id
        self.is_active = is_active


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


# --- P0-1: Access/Refresh Token 구분 ---------------------------------------

async def test_refresh_token_rejected_by_access_token_dependency():
    refresh_token = create_refresh_token(data={"sub": "1"})

    with pytest.raises(HTTPException) as exc:
        await get_current_user(_bearer(refresh_token), db=None)

    assert exc.value.status_code == 401


async def test_access_token_rejected_by_refresh_token_dependency():
    access_token = create_access_token(data={"sub": "1"})

    with pytest.raises(HTTPException) as exc:
        await get_refresh_token(db=None, refresh_token=access_token)

    assert exc.value.status_code == 401


# --- P1-3: 비활성 사용자 토큰 거부 -------------------------------------------

async def test_inactive_user_access_token_rejected(monkeypatch):
    access_token = create_access_token(data={"sub": "1"})

    async def fake_get_user_by_id(db, user_id):
        return FakeUser(id=user_id, is_active=False)

    monkeypatch.setattr(
        "app.core.security.get_user_by_id", fake_get_user_by_id
    )

    with pytest.raises(HTTPException) as exc:
        await get_current_user(_bearer(access_token), db=None)

    assert exc.value.status_code == 401


async def test_active_user_access_token_accepted(monkeypatch):
    access_token = create_access_token(data={"sub": "1"})

    async def fake_get_user_by_id(db, user_id):
        return FakeUser(id=user_id, is_active=True)

    monkeypatch.setattr(
        "app.core.security.get_user_by_id", fake_get_user_by_id
    )

    user_id = await get_current_user(_bearer(access_token), db=None)
    assert user_id == 1


# --- P1-5: 필수 claim 누락 시 500이 아니라 401 -------------------------------

async def test_token_without_sub_returns_401_not_500():
    token_without_sub = create_access_token(data={})

    with pytest.raises(HTTPException) as exc:
        await get_current_user(_bearer(token_without_sub), db=None)

    assert exc.value.status_code == 401


# --- P1-6: 휴대폰 번호 형식 검증 --------------------------------------------

VALID_USER_PAYLOAD = dict(
    email="user@example.com",
    password="Password1234!",
    name="홍길동",
    department="MEDICAL",
    gender="M",
)


def test_register_rejects_invalid_phone_number_format():
    with pytest.raises(ValidationError):
        UserCreateRequest(**VALID_USER_PAYLOAD, phone_number="01012345678")


def test_register_accepts_valid_phone_number_format():
    request = UserCreateRequest(**VALID_USER_PAYLOAD, phone_number="010-1234-5678")
    assert request.phone_number == "010-1234-5678"


def test_update_rejects_invalid_phone_number_format():
    with pytest.raises(ValidationError):
        UserUpdateRequest(phone_number="010-123-4567")


# --- P2-8: DB IntegrityError -> 409 -----------------------------------------

async def test_register_duplicate_race_returns_409(monkeypatch):
    from sqlalchemy.exc import IntegrityError

    async def fake_get_user_by_email(db, email):
        return None

    async def fake_get_user_by_phone_number(db, phone_number):
        return None

    async def fake_create_user(db, user):
        raise IntegrityError("insert", {}, Exception("duplicate"))

    async def fake_rollback():
        return None

    class FakeDB:
        rollback = staticmethod(fake_rollback)

    monkeypatch.setattr(user_service, "get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr(user_service, "get_user_by_phone_number", fake_get_user_by_phone_number)
    monkeypatch.setattr(user_service, "create_user", fake_create_user)
    # SQLAlchemy User() 인스턴스화는 리뷰와 무관한 별개의 매퍼 설정 오류
    # (xray_image.py의 back_populates="uploaded_xray_images"가 User 쪽에
    # 대응 relationship이 없어 발생)를 건드리므로, 이 유닛 테스트에서는
    # 단순 네임스페이스 객체로 대체해 IntegrityError -> 409 변환 로직만 검증한다.
    monkeypatch.setattr(user_service, "User", lambda **kwargs: SimpleNamespace(**kwargs))

    body = UserCreateRequest(**VALID_USER_PAYLOAD, phone_number="010-1234-5678")

    with pytest.raises(HTTPException) as exc:
        await user_service.register_user(FakeDB(), body)

    assert exc.value.status_code == 409
