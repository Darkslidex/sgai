"""Tests del módulo de cifrado DataEncryptor."""

import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.adapters.persistence.encryption import DataEncryptor


@pytest.fixture
def encryptor():
    key = Fernet.generate_key().decode()
    return DataEncryptor(key)


def test_encrypt_decrypt_roundtrip(encryptor):
    """encrypt → decrypt produce el mismo valor original."""
    original = "dato_sensible_123"
    encrypted = encryptor.encrypt(original)
    assert encryptor.decrypt(encrypted) == original


def test_encrypted_value_differs_from_original(encryptor):
    """El valor cifrado es diferente al original."""
    original = "peso_80.5"
    encrypted = encryptor.encrypt(original)
    assert encrypted != original


def test_decrypt_with_wrong_key_raises():
    """Descifrar con una clave incorrecta lanza InvalidToken."""
    key1 = Fernet.generate_key().decode()
    key2 = Fernet.generate_key().decode()
    enc1 = DataEncryptor(key1)
    enc2 = DataEncryptor(key2)

    encrypted = enc1.encrypt("secreto")
    with pytest.raises(InvalidToken):
        enc2.decrypt(encrypted)


def test_encrypt_decrypt_float_roundtrip(encryptor):
    """encrypt_float → decrypt_float produce el mismo valor numérico."""
    value = 80.5
    encrypted = encryptor.encrypt_float(value)
    assert encryptor.decrypt_float(encrypted) == pytest.approx(value)
