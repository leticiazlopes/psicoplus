from django import forms

from accounts.models import Paciente, Sessao


class SessaoForm(forms.ModelForm):
    class Meta:
        model = Sessao
        fields = ["paciente", "data", "horario_inicio", "duracao_minutos", "valor"]

    def __init__(self, *args, **kwargs):
        psicologo = kwargs.pop("psicologo", None)
        super().__init__(*args, **kwargs)

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
