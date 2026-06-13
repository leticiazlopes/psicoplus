import uuid
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_cryptography.fields import encrypt


class Usuario(AbstractUser):
    class Perfil(models.TextChoices):
        PACIENTE = "paciente", "Paciente"
        PSICOLOGO = "psicologo", "Psicólogo"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True)
    nome = models.CharField(max_length=255)

    perfil = models.CharField(
        max_length=20,
        choices=Perfil.choices
    )
    
    codigo_recuperacao = models.CharField(max_length=6, blank=True, null=True)
    codigo_expiracao = models.DateTimeField(blank=True, null=True)
    token_definicao_senha = models.UUIDField(blank=True, null=True, unique=True)
    token_definicao_senha_expira_em = models.DateTimeField(blank=True, null=True)
    token_definicao_senha_usado_em = models.DateTimeField(blank=True, null=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

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
    

class Psicologo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name="psicologo"
    )

    crp = models.CharField(max_length=20, unique=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    ativo = models.BooleanField(default=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.usuario.nome} - CRP {self.crp}"
    

class Paciente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name="paciente",
        blank=True,
        null=True
    )

    psicologo = models.ForeignKey(
        Psicologo,
        on_delete=models.CASCADE,
        related_name="pacientes"
    )

    nome_completo = models.CharField(max_length=255)
    email = models.EmailField()
    telefone = models.CharField(max_length=20, blank=True, null=True)
    data_nascimento = models.DateField(blank=True, null=True)

    contato_emergencia_nome = models.CharField(max_length=255, blank=True, null=True)
    contato_emergencia_telefone = models.CharField(max_length=20, blank=True, null=True)

    ativo = models.BooleanField(default=True)
    aceita_lembrete_email = models.BooleanField(default=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome_completo


class SerieSessao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    psicologo = models.ForeignKey(
        Psicologo,
        on_delete=models.CASCADE,
        related_name="series_sessoes",
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name="series_sessoes",
    )

    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criada_em"]
        verbose_name = "Série de Sessões"
        verbose_name_plural = "Séries de Sessões"

    def __str__(self):
        return f"Série de {self.paciente.nome_completo}"


class Sessao(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        CONFIRMADA = "confirmada", "Confirmada"
        CANCELADA = "cancelada", "Cancelada"
        REALIZADA = "realizada", "Realizada"
        FALTA = "falta", "Falta"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    @property
    def pode_evoluir(self):
        """Retorna True apenas se o status for Realizada, 
        servindo de gancho de segurança para o prontuário."""
        return self.status == self.Status.REALIZADA
    
    psicologo = models.ForeignKey(
        Psicologo, 
        on_delete=models.CASCADE, 
        related_name="sessoes"
    )
    paciente = models.ForeignKey(
        Paciente, 
        on_delete=models.CASCADE, 
        related_name="sessoes"
    )
    serie = models.ForeignKey(
        SerieSessao,
        on_delete=models.SET_NULL,
        related_name="sessoes",
        blank=True,
        null=True,
    )
    
    data = models.DateField()
    horario_inicio = models.TimeField()
    duracao_minutos = models.PositiveIntegerField(default=50)
    posicao_na_serie = models.PositiveIntegerField(blank=True, null=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
    )

    atendido_por_plano = models.BooleanField(default=False, verbose_name="Atendido por Plano de Saúde")
    isento_pagamento = models.BooleanField(default=False, verbose_name="Isento de Pagamento")
    criado_em = models.DateTimeField(auto_now_add=True)
    
    
    token_confirmacao = models.UUIDField(default=uuid.uuid4, editable=False, null=True, blank=True)
    confirmado_por = models.CharField(max_length=20, blank=True, null=True) 
    confirmado_em = models.DateTimeField(blank=True, null=True)

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

    def __str__(self):
        return f"Sessão: {self.paciente.nome_completo} - {self.data} às {self.horario_inicio}"
    

class HistoricoStatusSessao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sessao = models.ForeignKey(
        Sessao, 
        on_delete=models.CASCADE, 
        related_name='historico_status'
    )
    status_anterior = models.CharField(max_length=20)
    status_novo = models.CharField(max_length=20)
    alterado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-alterado_em']

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