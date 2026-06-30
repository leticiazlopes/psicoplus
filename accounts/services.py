from django.conf import settings
from django.core.mail import send_mail


def enviar_email_definicao_senha(usuario):
    """
    Gera um novo token de definição de senha e envia o e-mail de ativação/redefinição
    para o usuário informado. Usado tanto no cadastro inicial do paciente quanto
    no reenvio manual feito pelo psicólogo.
    """
    usuario.gerar_token_definicao_senha()
    usuario.save(
        update_fields=[
            "token_definicao_senha",
            "token_definicao_senha_expira_em",
            "token_definicao_senha_usado_em",
        ]
    )

    dominio = "https://psicoplus.onrender.com" if not settings.DEBUG else "http://127.0.0.1:8000"
    link_ativacao = f"{dominio}/definir-senha/{usuario.token_definicao_senha}/"

    assunto = "Bem-vindo ao Psico+ | Defina sua senha de acesso"
    mensagem_texto = (
        f"Olá, {usuario.nome or 'Paciente'}.\n\n"
        f"Seu psicólogo realizou o seu cadastro na plataforma Psico+.\n"
        f"Para criar sua senha de acesso e ativar sua conta, clique no link abaixo:\n"
        f"{link_ativacao}\n\n"
        f"Atenção: Este link é de uso único e expira automaticamente em 48 horas."
    )

    send_mail(
        subject=assunto,
        message=mensagem_texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
        fail_silently=False,
    )