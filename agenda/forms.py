import datetime

from django import forms

from accounts.models import Paciente, Sessao


class SessaoForm(forms.ModelForm):
    eh_recorrente = forms.BooleanField(required=False)
    repeticoes = forms.IntegerField(required=False, min_value=2, max_value=52)

    class Meta:
        model = Sessao
        fields = ["paciente", "data", "horario_inicio", "duracao_minutos", "valor", "atendido_por_plano", "isento_pagamento"]

    def __init__(self, *args, **kwargs):
        psicologo = kwargs.pop("psicologo", None)
        super().__init__(*args, **kwargs)
        self.psicologo = psicologo

        if psicologo:
            self.fields["paciente"].queryset = Paciente.objects.filter(
                psicologo=psicologo,
                ativo=True,
            )

        tailwind_classes = (
            "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 "
            "text-sm text-slate-900 transition focus:border-primary focus:ring-primary"
        )
        for field in self.fields.values():
            field.widget.attrs["class"] = tailwind_classes

        self.fields["data"].widget = forms.DateInput(
            attrs={
                "type": "date",
                "class": tailwind_classes,
                "x-model": "dataSessao",
            }
        )
        self.fields["horario_inicio"].widget = forms.TimeInput(
            attrs={"type": "time", "class": tailwind_classes}
        )
        self.fields["repeticoes"].widget = forms.NumberInput(
            attrs={
                "min": 2,
                "max": 52,
                "placeholder": "Ex: 4, 8, 12",
                "class": tailwind_classes,
                "x-model": "repeticoesRecorrencia",
            }
        )

    def _validar_conflito_no_horario(
        self,
        data,
        horario_inicio,
        duracao_minutos,
        excluir_ids=None,
    ):
        inicio_novo = datetime.datetime.combine(data, horario_inicio)
        fim_novo = inicio_novo + datetime.timedelta(minutes=duracao_minutos)

        sessoes_no_dia = Sessao.objects.filter(
            psicologo=self.psicologo,
            data=data,
        )

        if excluir_ids:
            sessoes_no_dia = sessoes_no_dia.exclude(id__in=excluir_ids)

        if self.instance.pk:
            sessoes_no_dia = sessoes_no_dia.exclude(pk=self.instance.pk)

        for sessao in sessoes_no_dia:
            inicio_existente = datetime.datetime.combine(data, sessao.horario_inicio)
            fim_existente = inicio_existente + datetime.timedelta(
                minutes=sessao.duracao_minutos
            )

            if inicio_novo < fim_existente and fim_novo > inicio_existente:
                return False

        return True

    def clean(self):
        cleaned_data = super().clean()
        data = cleaned_data.get("data")
        horario_inicio = cleaned_data.get("horario_inicio")
        duracao_minutos = cleaned_data.get("duracao_minutos")
        valor = cleaned_data.get("valor")
        atendido_por_plano = cleaned_data.get("atendido_por_plano")
        isento_pagamento = cleaned_data.get("isento_pagamento")
        eh_recorrente = cleaned_data.get("eh_recorrente")
        repeticoes = cleaned_data.get("repeticoes")

        if data and data < datetime.date.today():
            raise forms.ValidationError(
                "A data do agendamento deve ser hoje ou uma data futura."
            )

        if atendido_por_plano or isento_pagamento:
            cleaned_data["valor"] = 0
        elif valor is None or valor <= 0:
            self.add_error(
                "valor",
                "Informe um valor maior que zero quando a sessão não for isenta nem atendida por plano.",
            )

        if eh_recorrente and not repeticoes:
            self.add_error(
                "repeticoes",
                "Informe por quantas semanas a sessão deve se repetir.",
            )

        if not eh_recorrente:
            cleaned_data["repeticoes"] = None

        if not all([self.psicologo, data, horario_inicio, duracao_minutos]):
            return cleaned_data

        total_ocorrencias = repeticoes if eh_recorrente and repeticoes else 1
        for indice in range(total_ocorrencias):
            data_ocorrencia = data + datetime.timedelta(days=7 * indice)
            if not self._validar_conflito_no_horario(
                data_ocorrencia,
                horario_inicio,
                duracao_minutos,
            ):
                raise forms.ValidationError(
                    (
                        "Já existe um agendamento nesse horário para "
                        f"{data_ocorrencia.strftime('%d/%m/%Y')}. "
                        "Escolha outro intervalo."
                    )
                )

        return cleaned_data
