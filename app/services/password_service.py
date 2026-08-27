from argon2 import PasswordHasher
from argon2.exceptions import VerificationError


class PasswordService:
    password_hasher = PasswordHasher()

    @classmethod
    def hash_password(cls, password: str) -> str:
        return cls.password_hasher.hash(password)

    @classmethod
    def verify_password(cls, password: str, hashed_password: str) -> bool:
        try:
            return cls.password_hasher.verify(hashed_password, password)
        except VerificationError:
            return False