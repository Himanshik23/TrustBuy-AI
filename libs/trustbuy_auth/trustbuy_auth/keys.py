"""Dev-only RSA keypair bootstrap for JWT signing (RS256).

In production the keypair lives in AWS Secrets Manager (docs/SECURITY.md
§3) and is never generated at runtime. Locally, `ensure_keypair` lets
`docker compose up` work with zero manual setup: the Authentication
Service generates a keypair into a shared volume on first boot if one
doesn't already exist; the Gateway only ever reads the public half.
"""

from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def ensure_keypair(private_path: Path, public_path: Path, key_size: int = 2048) -> bool:
    """Create an RSA keypair at the given paths if one doesn't already
    exist. Returns True if a new keypair was generated."""
    if private_path.exists() and public_path.exists():
        return False

    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)

    key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)

    private_bytes = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_path.write_bytes(private_bytes)
    public_path.write_bytes(public_bytes)
    return True
