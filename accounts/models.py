from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

# Create your models here.
class Usuario(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    nome = models.CharField(max_length=255)
    crp = models.CharField(max_length=20, unique=True, null=True, blank=True)
    
    PERFIS = (
        ('paciente', 'Paciente'),
        ('psicologo', 'Psicólogo'),
    )
    
    perfil = models.CharField(max_length=20, choices=PERFIS)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'nome']

    def __str__(self):
        return f"{self.nome} - {self.email}"
2