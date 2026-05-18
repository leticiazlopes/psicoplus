from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid


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

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome"]

    def __str__(self):
        return f"{self.nome} - {self.email}"
    

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
    
class Sessao(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        CONFIRMADA = "confirmada", "Confirmada"
        CANCELADA = "cancelada", "Cancelada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
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
    
    data = models.DateField()
    horario_inicio = models.TimeField()
    duracao_minutos = models.PositiveIntegerField(default=50) # Duração em minutos (ex: 50, 60)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
    )

    atendido_por_plano = models.BooleanField(default=False, verbose_name="Atendido por Plano de Saúde")
    isento_pagamento = models.BooleanField(default=False, verbose_name="Isento de Pagamento")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data', '-horario_inicio']

    def __str__(self):
        return f"Sessão: {self.paciente.nome_completo} - {self.data} às {self.horario_inicio}"
    
