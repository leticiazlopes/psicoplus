from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction

from .models import Usuario, Psicologo


class LoginUsuarioForm(AuthenticationForm):
    username = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "seu@email.com",
                "autocomplete": "email",
            }
        ),
    )

    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Digite sua senha",
                "autocomplete": "current-password",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update(
                {
                    "class": "w-full rounded-xl border border-slate-200 bg-white py-3 pl-10 pr-4 text-[14px] text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-primary focus:ring-4 focus:ring-primary/10",
                }
            )


class CadastroPsicologoForm(UserCreationForm):
    nome = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "Nome completo"})
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "email@exemplo.com"})
    )

    crp = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={"placeholder": "Ex: 13/12345"})
    )

    telefone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "(83) 99999-9999"})
    )

    class Meta:
        model = Usuario
        fields = [
            "nome",
            "email",
            "crp",
            "telefone",
            "password1",
            "password2",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                "class": "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-[14px] text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-primary focus:ring-4 focus:ring-primary/10"
            })

        self.fields["password1"].widget.attrs.update({
            "placeholder": "Digite uma senha segura"
        })

        self.fields["password2"].widget.attrs.update({
            "placeholder": "Confirme a senha"
        })

    def clean_email(self):
        email = self.cleaned_data["email"]

        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("E-mail já cadastrado.")

        return email

    def clean_crp(self):
        crp = self.cleaned_data["crp"]

        if Psicologo.objects.filter(crp=crp).exists():
            raise forms.ValidationError("CRP já cadastrado.")

        return crp

    @transaction.atomic
    def save(self, commit=True):
        usuario = super().save(commit=False)

        usuario.email = self.cleaned_data["email"]
        usuario.username = self.cleaned_data["email"]
        usuario.nome = self.cleaned_data["nome"]
        usuario.perfil = "psicologo"

        if commit:
            usuario.save()

            Psicologo.objects.create(
                usuario=usuario,
                crp=self.cleaned_data["crp"],
                telefone=self.cleaned_data["telefone"]
            )

        return usuario
