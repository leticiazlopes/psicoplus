import datetime

from django import forms

from accounts.models import Paciente, Sessao


class SessaoForm(forms.ModelForm):
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
            attrs={"type": "date", "class": tailwind_classes}
        )
        self.fields["horario_inicio"].widget = forms.TimeInput(
            attrs={"type": "time", "class": tailwind_classes}
        )

    def clean(self):
        cleaned_data = super().clean()
        data = cleaned_data.get("data")
        horario_inicio = cleaned_data.get("horario_inicio")
        duracao_minutos = cleaned_data.get("duracao_minutos")
        valor = cleaned_data.get("valor")
        atendido_por_plano = cleaned_data.get("atendido_por_plano")
        isento_pagamento = cleaned_data.get("isento_pagamento")

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

        if not all([self.psicologo, data, horario_inicio, duracao_minutos]):
            return cleaned_data

        inicio_novo = datetime.datetime.combine(data, horario_inicio)
        fim_novo = inicio_novo + datetime.timedelta(minutes=duracao_minutos)

        sessoes_no_dia = Sessao.objects.filter(
            psicologo=self.psicologo,
            data=data,
        )

        if self.instance.pk:
            sessoes_no_dia = sessoes_no_dia.exclude(pk=self.instance.pk)

        for sessao in sessoes_no_dia:
            inicio_existente = datetime.datetime.combine(data, sessao.horario_inicio)
            fim_existente = inicio_existente + datetime.timedelta(
                minutes=sessao.duracao_minutos
            )

            if inicio_novo < fim_existente and fim_novo > inicio_existente:
                raise forms.ValidationError(
                    "Já existe um agendamento nesse horário. Escolha outro intervalo."
                )

        return cleaned_data
