import uuid
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_cryptography.fields import encrypt


class Usuario(AbstractUser):
    class Perfil(models.TextChoices):
        PACIENTE = "paciente", _("Paciente")
        PSICOLOGO = "psicologo", _("Psicólogo")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    username = models.CharField(max_length=150, unique=True, blank=True, null=True, verbose_name=_("nome de usuário"))
    email = models.EmailField(unique=True, verbose_name=_("e-mail"))
    nome = models.CharField(max_length=255, verbose_name=_("nome"))

    perfil = models.CharField(
        max_length=20,
        choices=Perfil.choices,
        verbose_name=_("perfil"),
    )
    
    codigo_recuperacao = models.CharField(max_length=6, blank=True, null=True, verbose_name=_("código de recuperação"))
    codigo_expiracao = models.DateTimeField(blank=True, null=True, verbose_name=_("expiração do código"))
    token_definicao_senha = models.UUIDField(blank=True, null=True, unique=True, verbose_name=_("token de definição de senha"))
    token_definicao_senha_expira_em = models.DateTimeField(blank=True, null=True, verbose_name=_("expiração do token de definição de senha"))
    token_definicao_senha_usado_em = models.DateTimeField(blank=True, null=True, verbose_name=_("uso do token de definição de senha"))

    criado_em = models.DateTimeField(auto_now_add=True, verbose_name=_("criado em"))
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name=_("atualizado em"))

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome"]

    def __str__(self):
        return f"{self.nome} - {self.email}"

    def gerar_token_definicao_senha(self):
        self.token_definicao_senha = uuid.uuid4()
        self.token_definicao_senha_expira_em = timezone.now() + timedelta(hours=48)
        self.token_definicao_senha_usado_em = None

    def token_definicao_senha_esta_valido(self):
        if not self.token_definicao_senha or not self.token_definicao_senha_expira_em:
            return False

        if self.token_definicao_senha_usado_em:
            return False

        return timezone.now() <= self.token_definicao_senha_expira_em

    def marcar_token_definicao_senha_como_usado(self):
        self.token_definicao_senha_usado_em = timezone.now()

    class Meta:
        verbose_name = _("usuário")
        verbose_name_plural = _("usuários")
    

class Psicologo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name="psicologo",
        verbose_name=_("usuário"),
    )

    crp = models.CharField(max_length=20, unique=True, verbose_name=_("CRP"))
    telefone = models.CharField(max_length=20, blank=True, null=True, verbose_name=_("telefone"))
    bio = models.TextField(blank=True, null=True, verbose_name=_("bio"))

    ativo = models.BooleanField(default=True, verbose_name=_("ativo"))

    criado_em = models.DateTimeField(auto_now_add=True, verbose_name=_("criado em"))
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name=_("atualizado em"))

    def __str__(self):
        return f"{self.usuario.nome} - CRP {self.crp}"

    class Meta:
        verbose_name = _("psicólogo")
        verbose_name_plural = _("psicólogos")
    

class Paciente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name="paciente",
        blank=True,
        null=True,
        verbose_name=_("usuário"),
    )

    psicologo = models.ForeignKey(
        Psicologo,
        on_delete=models.CASCADE,
        related_name="pacientes",
        verbose_name=_("psicólogo"),
    )

    nome_completo = models.CharField(max_length=255, verbose_name=_("nome completo"))
    email = models.EmailField(verbose_name=_("e-mail"))
    telefone = models.CharField(max_length=20, blank=True, null=True, verbose_name=_("telefone"))
    data_nascimento = models.DateField(blank=True, null=True, verbose_name=_("data de nascimento"))

    contato_emergencia_nome = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("nome do contato de emergência"))
    contato_emergencia_telefone = models.CharField(max_length=20, blank=True, null=True, verbose_name=_("telefone de emergência"))

    ativo = models.BooleanField(default=True, verbose_name=_("ativo"))
    aceita_lembrete_email = models.BooleanField(default=True, verbose_name=_("aceita lembrete por e-mail"))

    criado_em = models.DateTimeField(auto_now_add=True, verbose_name=_("criado em"))
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name=_("atualizado em"))

    def __str__(self):
        return self.nome_completo

    class Meta:
        verbose_name = _("paciente")
        verbose_name_plural = _("pacientes")


class SerieSessao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    psicologo = models.ForeignKey(
        Psicologo,
        on_delete=models.CASCADE,
        related_name="series_sessoes",
        verbose_name=_("psicólogo"),
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name="series_sessoes",
        verbose_name=_("paciente"),
    )

    criada_em = models.DateTimeField(auto_now_add=True, verbose_name=_("criada em"))

    class Meta:
        ordering = ["-criada_em"]
        verbose_name = _("série de sessões")
        verbose_name_plural = _("séries de sessões")

    def __str__(self):
        return f"Série de {self.paciente.nome_completo}"


class Sessao(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pendente", _("Pendente")
        CONFIRMADA = "confirmada", _("Confirmada")
        CANCELADA = "cancelada", _("Cancelada")
        REALIZADA = "realizada", _("Realizada")
        FALTA = "falta", _("Falta")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    @property
    def pode_evoluir(self):
        """Retorna True apenas se o status for Realizada, 
        servindo de gancho de segurança para o prontuário."""
        return self.status == self.Status.REALIZADA
    
    psicologo = models.ForeignKey(
        Psicologo, 
        on_delete=models.CASCADE, 
        related_name="sessoes",
        verbose_name=_("psicólogo"),
    )
    paciente = models.ForeignKey(
        Paciente, 
        on_delete=models.CASCADE, 
        related_name="sessoes",
        verbose_name=_("paciente"),
    )
    serie = models.ForeignKey(
        SerieSessao,
        on_delete=models.SET_NULL,
        related_name="sessoes",
        blank=True,
        null=True,
        verbose_name=_("série"),
    )
    
    data = models.DateField(verbose_name=_("data"))
    horario_inicio = models.TimeField(verbose_name=_("horário de início"))
    duracao_minutos = models.PositiveIntegerField(default=50, verbose_name=_("duração em minutos"))
    posicao_na_serie = models.PositiveIntegerField(blank=True, null=True, verbose_name=_("posição na série"))
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("valor"))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
        verbose_name=_("status"),
    )

    atendido_por_plano = models.BooleanField(default=False, verbose_name=_("atendido por plano de saúde"))
    isento_pagamento = models.BooleanField(default=False, verbose_name=_("isento de pagamento"))
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name=_("criado em"))
    
    
    token_confirmacao = models.UUIDField(default=uuid.uuid4, editable=False, null=True, blank=True, verbose_name=_("token de confirmação"))
    confirmado_por = models.CharField(max_length=20, blank=True, null=True, verbose_name=_("confirmado por")) 
    confirmado_em = models.DateTimeField(blank=True, null=True, verbose_name=_("confirmado em"))

    @property
    def link_expirado(self):
        """Retorna True se a data/hora da sessão já passou no presente"""
        from django.utils import timezone
        import datetime
        
        
        data_hora_sessao = timezone.make_aware(
            datetime.datetime.combine(self.data, self.horario_inicio)
        )
        return timezone.now() > data_hora_sessao

    class Meta:
        ordering = ['-data', '-horario_inicio']
        constraints = [
            models.UniqueConstraint(
                fields=["serie", "posicao_na_serie"],
                name="unique_posicao_na_serie_por_serie",
            ),
        ]
        verbose_name = _("sessão")
        verbose_name_plural = _("sessões")

    def __str__(self):
        return f"Sessão: {self.paciente.nome_completo} - {self.data} às {self.horario_inicio}"
    

class HistoricoStatusSessao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sessao = models.ForeignKey(
        Sessao, 
        on_delete=models.CASCADE, 
        related_name='historico_status',
        verbose_name=_("sessão"),
    )
    status_anterior = models.CharField(max_length=20, verbose_name=_("status anterior"))
    status_novo = models.CharField(max_length=20, verbose_name=_("novo status"))
    alterado_em = models.DateTimeField(auto_now_add=True, verbose_name=_("alterado em"))
    
    class Meta:
        ordering = ['-alterado_em']
        verbose_name = _("histórico de status da sessão")
        verbose_name_plural = _("históricos de status da sessão")

    def __str__(self):
        return f"{self.sessao.paciente.nome_completo}: {self.status_anterior} -> {self.status_novo}"






@receiver(post_save, sender=Sessao)
def registrar_historico_status(sender, instance, created, **kwargs):
    """
    Intercapta o salvamento da Sessão para gerar logs automaticamente.
    Mantém o histórico limpo e centralizado no servidor.
    """
    if created:
        
        HistoricoStatusSessao.objects.create(
            sessao=instance,
            status_anterior='criado',
            status_novo=instance.status
        )
    else:
        
        
        original = Sessao.objects.filter(pk=instance.pk).first()
        if original and original.status != instance.status:
            HistoricoStatusSessao.objects.create(
                sessao=instance,
                status_anterior=original.status,
                status_novo=instance.status
            )

class DiarioPensamento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name="diarios"
    )
    
    situacao = encrypt(models.TextField(verbose_name="Situação"))
    emocao_principal = models.CharField(max_length=100, verbose_name="Emoção Principal", blank=True, null=True)
    
    intensidade = models.PositiveIntegerField(
        verbose_name="Intensidade",
        choices=[(i, str(i)) for i in range(1, 6)]  
    )
    
    observacoes_livres = encrypt(models.TextField(blank=True, null=True, verbose_name="Observações Livres"))
    
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Diário de Pensamento"
        verbose_name_plural = "Diário de Pensamentos"

    def __str__(self):
        return f"Registro de {self.paciente.nome_completo} em {self.criado_em.strftime('%d/%m/%Y %H:%M')}"
