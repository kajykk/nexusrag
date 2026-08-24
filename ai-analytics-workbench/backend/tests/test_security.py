"""security.py 测试：密码哈希 + JWT token（P0 新增）。"""

import time

import jwt

from app.config import settings
from app.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_password_returns_str(self):
        hashed = hash_password("password123")
        assert isinstance(hashed, str)
        assert hashed != "password123"

    def test_hash_password_is_salt_randomized(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # 不同盐值

    def test_verify_password_correct(self):
        hashed = hash_password("secret")
        assert verify_password("secret", hashed) is True

    def test_verify_password_wrong(self):
        hashed = hash_password("secret")
        assert verify_password("wrong", hashed) is False

    def test_verify_password_invalid_hash(self):
        assert verify_password("any", "not-a-valid-hash") is False

    def test_verify_password_empty(self):
        assert verify_password("", hash_password("x")) is False


class TestJWTToken:
    def test_create_token_returns_str(self):
        token = create_access_token(subject=42)
        assert isinstance(token, str)
        assert token.count(".") == 2  # header.payload.signature

    def test_decode_valid_token(self):
        token = create_access_token(subject=42)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_invalid_token(self):
        assert decode_token("not.a.jwt") is None
        assert decode_token("") is None
        assert decode_token("invalid") is None

    def test_decode_token_wrong_secret(self):
        token = jwt.encode(
            {"sub": "1", "type": "access", "exp": int(time.time()) + 3600},
            "wrong-secret",
            algorithm=settings.JWT_ALGORITHM,
        )
        assert decode_token(token) is None

    def test_token_contains_access_type(self):
        token = create_access_token(subject=1)
        payload = decode_token(token)
        assert payload["type"] == "access"

    def test_custom_expiration(self):
        from datetime import timedelta

        token = create_access_token(subject=1, expires_delta=timedelta(seconds=1))
        # 立即可用
        assert decode_token(token) is not None
        # 等待过期
        time.sleep(2)
        assert decode_token(token) is None
