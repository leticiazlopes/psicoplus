import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.models import Paciente, Psicologo, Sessao


class Prontuario(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    sessao = models.ForeignKey(
        Sessao,
        on_delete=models.PROTECT,
        related_name="prontuarios",
        verbose_name=_("sessão"),
    )
    psicologo = models.ForeignKey(
        Psicologo,
        on_delete=models.PROTECT,
        related_name="prontuarios",
        null=True,
        verbose_name=_("psicólogo"),
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        related_name="prontuarios",
        null=True,
        verbose_name=_("paciente"),
    )
    texto = models.TextField(verbose_name=_("texto"))
    humor_paciente = models.IntegerField(blank=True, null=True, verbose_name=_("humor do paciente"))
    riscos_identificados = models.TextField(blank=True, null=True, verbose_name=_("riscos identificados"))
    plano_terapeutico = models.TextField(blank=True, verbose_name=_("plano terapêutico"))
    criptografado = models.BooleanField(default=True, verbose_name=_("criptografado"))
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name=_("criado em"))
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name=_("atualizado em"))

    class Meta:
        ordering = ["-sessao__data", "-criado_em"]
        verbose_name = _("prontuário")
        verbose_name_plural = _("prontuários")

    def __str__(self):
        return f"Prontuario de {self.sessao.paciente.nome_completo} em {self.sessao.data:%d/%m/%Y}"
