import base64
import hashlib

from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
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

    try:
        return _get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        # Mantém compatibilidade com registros legados ainda salvos em texto puro.
        return value


def encrypt_prontuario_payload(payload):
    encrypted = payload.copy()

    for field in SENSITIVE_FIELDS:
        encrypted[field] = encrypt_value(encrypted.get(field))

    return encrypted


def anonymize_supervisao_text(value, prontuario):
    if not value:
        return value

    paciente = prontuario.paciente
    replacements = [
        (paciente.nome_completo, "[PACIENTE]"),
        (paciente.email, "[E-MAIL REMOVIDO]"),
        (paciente.telefone, "[TELEFONE REMOVIDO]"),
        (paciente.contato_emergencia_nome, "[CONTATO DE EMERGENCIA REMOVIDO]"),
        (paciente.contato_emergencia_telefone, "[TELEFONE DE EMERGENCIA REMOVIDO]"),
    ]

    if paciente.data_nascimento:
        replacements.append((paciente.data_nascimento.strftime("%d/%m/%Y"), "[DATA DE NASCIMENTO REMOVIDA]"))

    anonymized = value
    for original, replacement in replacements:
        if original:
            anonymized = anonymized.replace(original, replacement)

    return anonymized


def serialize_prontuario(prontuario):
    return {
        "id": str(prontuario.id),
        "sessao_id": str(prontuario.sessao_id),
        "psicologo_id": str(prontuario.psicologo_id),
        "paciente_id": str(prontuario.paciente_id),
        "texto": decrypt_value(prontuario.texto),
        "humor_paciente": prontuario.humor_paciente,
        "riscos_identificados": decrypt_value(prontuario.riscos_identificados),
        "plano_terapeutico": decrypt_value(prontuario.plano_terapeutico),
        "criptografado": prontuario.criptografado,
        "data_sessao": prontuario.sessao.data.isoformat(),
        "data_sessao_formatada": prontuario.sessao.data.strftime("%d/%m/%Y"),
        "horario_sessao": prontuario.sessao.horario_inicio.strftime("%H:%M"),
        "duracao_minutos": prontuario.sessao.duracao_minutos,
        "status_sessao": prontuario.sessao.status,
        "serie_id": str(prontuario.sessao.serie_id) if prontuario.sessao.serie_id else None,
        "posicao_na_serie": prontuario.sessao.posicao_na_serie,
        "total_sessoes_serie": (
            prontuario.sessao.serie.sessoes.count() if prontuario.sessao.serie_id else None
        ),
    }


def serialize_prontuario_supervisao(prontuario):
    return {
        "id": str(prontuario.id),
        "texto": anonymize_supervisao_text(decrypt_value(prontuario.texto), prontuario),
        "humor_paciente": prontuario.humor_paciente,
        "riscos_identificados": anonymize_supervisao_text(decrypt_value(prontuario.riscos_identificados), prontuario),
        "plano_terapeutico": anonymize_supervisao_text(decrypt_value(prontuario.plano_terapeutico), prontuario),
        "duracao_minutos": prontuario.sessao.duracao_minutos,
        "status_sessao": prontuario.sessao.get_status_display(),
        "serie_id": str(prontuario.sessao.serie_id) if prontuario.sessao.serie_id else None,
        "posicao_na_serie": prontuario.sessao.posicao_na_serie,
        "total_sessoes_serie": (
            prontuario.sessao.serie.sessoes.count() if prontuario.sessao.serie_id else None
        ),
    }
