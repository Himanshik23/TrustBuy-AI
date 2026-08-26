"""Unit tests for the auth building blocks that don't require a database -
password hashing and JWT issuance/verification. Full integration coverage
(signup -> login -> refresh against a real Postgres) is the documented
Phase 1 follow-up in docs/TESTING_STRATEGY.md §2 (testcontainers-python).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from trustbuy_auth.keys import ensure_keypair
from trustbuy_auth.password import hash_password, needs_rehash, verify_password
from trustbuy_auth.refresh import generate_refresh_token, hash_refresh_token


@pytest.fixture(scope="module", autouse=True)
def _dev_keypair():
    with tempfile.TemporaryDirectory() as tmp:
        private_path = Path(tmp) / "private.pem"
        public_path = Path(tmp) / "public.pem"
        ensure_keypair(private_path, public_path)
        os.environ["JWT_PRIVATE_KEY_PATH"] = str(private_path)
        os.environ["JWT_PUBLIC_KEY_PATH"] = str(public_path)
        yield


def test_password_hash_roundtrip():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_password_hash_is_argon2id():
    hashed = hash_password("correct horse battery staple")
    assert hashed.startswith("$argon2id$")


def test_needs_rehash_false_for_fresh_hash():
    hashed = hash_password("correct horse battery staple")
    assert needs_rehash(hashed) is False


def test_refresh_token_hash_is_deterministic_and_opaque():
    token = generate_refresh_token()
    assert len(token) > 32
    assert hash_refresh_token(token) == hash_refresh_token(token)
    assert hash_refresh_token(token) != token


def test_access_token_roundtrip():
    from trustbuy_auth.jwt import create_access_token, decode_access_token

    token = create_access_token(subject="11111111-1111-1111-1111-111111111111", role="user")
    claims = decode_access_token(token)
    assert claims["sub"] == "11111111-1111-1111-1111-111111111111"
    assert claims["role"] == "user"
    assert claims["type"] == "access"


def test_access_token_rejects_tampering():
    from trustbuy_auth.jwt import TokenError, create_access_token, decode_access_token

    token = create_access_token(subject="11111111-1111-1111-1111-111111111111", role="user")
    tampered = token[:-4] + ("A" * 4)
    with pytest.raises(TokenError):
        decode_access_token(tampered)
