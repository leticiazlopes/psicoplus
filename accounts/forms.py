from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction

from .models import Usuario, Psicologo


class CadastroPsicologoForm(UserCreationForm):
    nome = forms.CharField(max_length=255)
    email = forms.EmailField()
    crp = forms.CharField(max_length=20)
    telefone = forms.CharField(required=False)

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