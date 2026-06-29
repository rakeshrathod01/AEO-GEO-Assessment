from app.core.security import decrypt_secret, encrypt_secret, mask_secret


def test_encrypt_roundtrip():
    secret = "sk-ant-super-secret-123"
    token = encrypt_secret(secret)
    assert token != secret  # actually encrypted
    assert decrypt_secret(token) == secret


def test_encrypt_is_nondeterministic_but_decryptable():
    a = encrypt_secret("same")
    b = encrypt_secret("same")
    assert a != b  # Fernet includes a random IV
    assert decrypt_secret(a) == decrypt_secret(b) == "same"


def test_mask_secret():
    assert mask_secret("sk-ant-abcd1234") == "***********1234"  # 15 chars -> 11 masked
    assert mask_secret("ab") == "**"
    assert mask_secret("") == ""
