"""
Utilidades de cifrado para datos sensibles de salud.
Usa Fernet (AES-128-CBC) para cifrado simétrico.
La clave se almacena en la variable de entorno ENCRYPTION_KEY.

Generar clave:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from cryptography.fernet import Fernet, InvalidToken


class DataEncryptor:
    """Cifrado simétrico Fernet para datos sensibles."""

    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, data: str) -> str:
        """Cifrar dato sensible. Retorna string base64 URL-safe."""
        return self._fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """Descifrar dato. Lanza InvalidToken si la clave es incorrecta."""
        return self._fernet.decrypt(encrypted_data.encode()).decode()

    def encrypt_float(self, value: float) -> str:
        """Cifrar un valor numérico como string."""
        return self.encrypt(str(value))

    def decrypt_float(self, encrypted_data: str) -> float:
        """Descifrar y convertir a float."""
        return float(self.decrypt(encrypted_data))
