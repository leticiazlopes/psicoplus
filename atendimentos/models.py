import uuid

from django.db import models
from django.utils import timezone
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


class CompartilhamentoSupervisao(models.Model):
    class Duracao(models.TextChoices):
        VINTE_QUATRO_HORAS = "24h", _("24 horas")
        SETE_DIAS = "7d", _("7 dias")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name=_("token"))
    prontuario = models.ForeignKey(
        Prontuario,
        on_delete=models.CASCADE,
        related_name="compartilhamentos_supervisao",
        verbose_name=_("prontuário"),
    )
    criado_por = models.ForeignKey(
        Psicologo,
        on_delete=models.CASCADE,
        related_name="compartilhamentos_supervisao",
        verbose_name=_("psicólogo"),
    )
    duracao = models.CharField(
        max_length=3,
        choices=Duracao.choices,
        verbose_name=_("duração do link"),
    )
    expira_em = models.DateTimeField(verbose_name=_("expira em"))
    ultimo_acesso_em = models.DateTimeField(blank=True, null=True, verbose_name=_("último acesso em"))
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name=_("criado em"))

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = _("compartilhamento de supervisão")
        verbose_name_plural = _("compartilhamentos de supervisão")

    @property
    def expirado(self):
        return timezone.now() >= self.expira_em

    def __str__(self):
        return f"Compartilhamento de supervisão {self.token}"


class LogAcessoCompartilhamentoSupervisao(models.Model):
    class Resultado(models.TextChoices):
        SUCESSO = "sucesso", _("Sucesso")
        EXPIRADO = "expirado", _("Expirado")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    compartilhamento = models.ForeignKey(
        CompartilhamentoSupervisao,
        on_delete=models.CASCADE,
        related_name="logs_acesso",
        verbose_name=_("compartilhamento"),
    )
    resultado = models.CharField(
        max_length=20,
        choices=Resultado.choices,
        verbose_name=_("resultado"),
    )
    ip_acesso = models.GenericIPAddressField(blank=True, null=True, verbose_name=_("IP de acesso"))
    user_agent = models.TextField(blank=True, verbose_name=_("user agent"))
    acessado_em = models.DateTimeField(auto_now_add=True, verbose_name=_("acessado em"))

    class Meta:
        ordering = ["-acessado_em"]
        verbose_name = _("log de acesso do compartilhamento de supervisão")
        verbose_name_plural = _("logs de acesso do compartilhamento de supervisão")

    def __str__(self):
        return f"{self.compartilhamento.token} - {self.resultado}"
