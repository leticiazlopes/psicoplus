import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings


SENSITIVE_FIELDS = ("texto", "riscos_identificados", "plano_terapeutico")


def _get_fernet():
    # Deriva uma chave estável da SECRET_KEY do Django para uso local no projeto.
    key = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_value(value):
    if not value:
        return value

    return _get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(value):
    if not value:
        return value

    return _get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")


def encrypt_prontuario_payload(payload):
    encrypted = payload.copy()

    for field in SENSITIVE_FIELDS:
        encrypted[field] = encrypt_value(encrypted.get(field))

    return encrypted
