import uuid

from django.db import models

from accounts.models import Paciente, Psicologo, Sessao


class Prontuario(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    sessao = models.ForeignKey(
        Sessao,
        on_delete=models.PROTECT,
        related_name="prontuarios",
    )
    psicologo = models.ForeignKey(
        Psicologo,
        on_delete=models.PROTECT,
        related_name="prontuarios",
        null=True,
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        related_name="prontuarios",
        null=True,
    )
    texto = models.TextField()
    humor_paciente = models.IntegerField(blank=True, null=True)
    riscos_identificados = models.TextField(blank=True, null=True)
    plano_terapeutico = models.TextField(blank=True)
    criptografado = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-sessao__data", "-criado_em"]
        verbose_name = "Prontuário"
        verbose_name_plural = "Prontuários"

    def __str__(self):
        return f"Prontuario de {self.sessao.paciente.nome_completo} em {self.sessao.data:%d/%m/%Y}"
