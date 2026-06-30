from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

Usuario = get_user_model()


@receiver(post_save, sender=Usuario)
def enviar_email_primeiro_acesso(sender, instance, created, **kwargs):
    if not created or instance.perfil != Usuario.Perfil.PACIENTE:
        return

    instance.gerar_token_definicao_senha()
    instance.save(
        update_fields=[
            "token_definicao_senha",
            "token_definicao_senha_expira_em",
            "token_definicao_senha_usado_em",
        ]
    )

    dominio = "https://psicoplus.onrender.com" if not settings.DEBUG else "http://127.0.0.1:8000"
    link_ativacao = f"{dominio}/definir-senha/{instance.token_definicao_senha}/"

    assunto = "Bem-vindo ao Psico+ | Defina sua senha de acesso"
    mensagem_texto = (
        f"Olá, {instance.nome or 'Paciente'}.\n\n"
        f"Seu psicólogo realizou o seu cadastro na plataforma Psico+.\n"
        f"Para criar sua senha de acesso e ativar sua conta, clique no link abaixo:\n"
        f"{link_ativacao}\n\n"
        f"Atenção: Este link é de uso único e expira automaticamente em 48 horas."
    )

    send_mail(
        subject=assunto,
        message=mensagem_texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[instance.email],
        fail_silently=False,
    )