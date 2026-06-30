from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .services import enviar_email_definicao_senha

Usuario = get_user_model()


@receiver(post_save, sender=Usuario)
def enviar_email_primeiro_acesso(sender, instance, created, **kwargs):
    if not created or instance.perfil != Usuario.Perfil.PACIENTE:
        return

    enviar_email_definicao_senha(instance)