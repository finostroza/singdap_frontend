import base64
import json

def decode_jwt(token: str) -> dict:
    """
    Decodifica un JWT sin validar la firma.
    Útil solo para leer datos (userId, email, etc).
    """
    try:
        payload_part = token.split(".")[1]

        # Padding Base64
        padding = "=" * (-len(payload_part) % 4)
        payload_part += padding

        decoded_bytes = base64.urlsafe_b64decode(payload_part)
        return json.loads(decoded_bytes.decode("utf-8"))

    except Exception as e:
        raise ValueError(f"Token inválido: {e}")
