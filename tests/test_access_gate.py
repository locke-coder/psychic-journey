import hashlib

from app import verify_access_password


def test_verify_access_password_accepts_plain_configured_password() -> None:
    assert verify_access_password(
        "invite-only",
        configured_password="invite-only",
    )


def test_verify_access_password_rejects_wrong_plain_password() -> None:
    assert not verify_access_password(
        "wrong-password",
        configured_password="invite-only",
    )


def test_verify_access_password_accepts_sha256_configured_password_hash() -> None:
    digest = hashlib.sha256("invite-only".encode("utf-8")).hexdigest()

    assert verify_access_password(
        "invite-only",
        configured_password_hash=digest,
    )


def test_verify_access_password_requires_configured_credentials() -> None:
    assert not verify_access_password("invite-only")
