import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0016_sessao_data_pagamento_sessao_forma_pagamento_and_more"),
        ("atendimentos", "0002_alter_prontuario_options_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompartilhamentoSupervisao",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="token")),
                ("duracao", models.CharField(choices=[("24h", "24 horas"), ("7d", "7 dias")], max_length=3, verbose_name="duração do link")),
                ("expira_em", models.DateTimeField(verbose_name="expira em")),
                ("ultimo_acesso_em", models.DateTimeField(blank=True, null=True, verbose_name="último acesso em")),
                ("criado_em", models.DateTimeField(auto_now_add=True, verbose_name="criado em")),
                ("criado_por", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="compartilhamentos_supervisao", to="accounts.psicologo", verbose_name="psicólogo")),
                ("prontuario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="compartilhamentos_supervisao", to="atendimentos.prontuario", verbose_name="prontuário")),
            ],
            options={
                "verbose_name": "compartilhamento de supervisão",
                "verbose_name_plural": "compartilhamentos de supervisão",
                "ordering": ["-criado_em"],
            },
        ),
        migrations.CreateModel(
            name="LogAcessoCompartilhamentoSupervisao",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("resultado", models.CharField(choices=[("sucesso", "Sucesso"), ("expirado", "Expirado")], max_length=20, verbose_name="resultado")),
                ("ip_acesso", models.GenericIPAddressField(blank=True, null=True, verbose_name="IP de acesso")),
                ("user_agent", models.TextField(blank=True, verbose_name="user agent")),
                ("acessado_em", models.DateTimeField(auto_now_add=True, verbose_name="acessado em")),
                ("compartilhamento", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="logs_acesso", to="atendimentos.compartilhamentosupervisao", verbose_name="compartilhamento")),
            ],
            options={
                "verbose_name": "log de acesso do compartilhamento de supervisão",
                "verbose_name_plural": "logs de acesso do compartilhamento de supervisão",
                "ordering": ["-acessado_em"],
            },
        ),
    ]
