"""Firma HMAC para comunicación inter-servicio SGAI ↔ Ana.

Previene que terceros fabriquen requests entre los servicios.
Usa SHA-256 con timestamp para prevenir replay attacks.
"""

import hashlib
import hmac
import time
from typing import Optional


def sign_request(body: bytes, secret: str, timestamp: Optional[int] = None) -> dict:
    """Genera headers de firma HMAC para una request saliente.

    Retorna dict con X-SGAI-Timestamp y X-SGAI-Signature para incluir en headers.
    """
    ts = timestamp or int(time.time())
    message = f"{ts}.{body.decode(errors='replace')}".encode()
    signature = hmac.new(
        secret.encode(),
        message,
        hashlib.sha256,
    ).hexdigest()
    return {
        "X-SGAI-Timestamp": str(ts),
        "X-SGAI-Signature": signature,
    }


def verify_request(
    body: bytes,
    secret: str,
    timestamp: str,
    signature: str,
    max_age: int = 300,
) -> bool:
    """Verifica la firma HMAC de una request entrante.

    Rechaza si el timestamp tiene más de max_age segundos (anti-replay).
    Usa compare_digest para prevenir timing attacks.
    """
    try:
        ts_int = int(timestamp)
    except (ValueError, TypeError):
        return False

    if abs(time.time() - ts_int) > max_age:
        return False

    message = f"{timestamp}.{body.decode(errors='replace')}".encode()
    expected = hmac.new(
        secret.encode(),
        message,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
