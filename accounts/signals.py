from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model

Usuario = get_user_model()

@receiver(post_save, sender=Usuario)
def enviar_email_primeiro_acesso(sender, instance, created, **kwargs):
    
    
    if created and getattr(instance, 'is_paciente', True): 
        
        
        token = default_token_generator.make_token(instance)
        uid = urlsafe_base64_encode(force_bytes(instance.pk))
        
        
        from django.conf import settings
        dominio = "https://psicoplus.onrender.com" if not settings.DEBUG else "http://127.0.0.1:8000"
        
        
        link_ativacao = f"{dominio}/definir-senha/{uid}/{token}/"        
        
        assunto = "Bem-vindo ao Psico+ | Defina sua senha de acesso"
        mensagem_texto = (
            f"Olá, {instance.first_name or 'Paciente'}.\n\n"
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