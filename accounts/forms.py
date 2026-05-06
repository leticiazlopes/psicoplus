from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction
from django.contrib.auth.hashers import check_password

from .models import Usuario, Psicologo
from .models import Paciente


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

class CadastroPacienteForm(forms.ModelForm):
    

    class Meta:
        model = Paciente
        fields = [
            "nome_completo",
            "email",
            "telefone",
            "data_nascimento",
            "contato_emergencia_nome",
            "contato_emergencia_telefone",
        ]
        widgets = {
            "nome_completo": forms.TextInput(attrs={"placeholder": "Nome completo do paciente"}),
            "email": forms.EmailInput(attrs={"placeholder": "email@paciente.com"}),
            "telefone": forms.TextInput(attrs={"placeholder": "(83) 99999-9999"}),
            "data_nascimento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "contato_emergencia_nome": forms.TextInput(attrs={"placeholder": "Nome do contato"}),
            "contato_emergencia_telefone": forms.TextInput(attrs={"placeholder": "Telefone de emergência"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-[14px] text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-primary focus:ring-4 focus:ring-primary/10"
            })

    def clean_email(self):
        email = self.cleaned_data.get("email")
        pacientes_com_esse_email = Paciente.objects.filter(email=email)
        
        if self.instance.pk:
            pacientes_com_esse_email = pacientes_com_esse_email.exclude(pk=self.instance.pk)
            
        if pacientes_com_esse_email.exists():
            raise forms.ValidationError("Este e-mail já está em uso por outro paciente.")
            
        return email

class MeuPerfilForm(forms.ModelForm):
    nome = forms.CharField(label="Nome Completo")
    email = forms.EmailField(label="E-mail")
    senha_atual = forms.CharField(
        label="Senha Atual para Confirmar", 
        widget=forms.PasswordInput(attrs={'placeholder': 'Digite sua senha atual'})
    )
    
    # Adicione estes dois se quiser permitir a troca no mesmo form, 
    # OU mantenha apenas a lógica de segurança se for usar a página separada.
    # Se for usar a página separada, apenas garanta que o save() não altere senhas.

    class Meta:
        model = Psicologo
        fields = ["crp", "telefone"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # ... (sua estilização de classes aqui) ...
        if self.instance and self.instance.usuario:
            self.fields["nome"].initial = self.instance.usuario.nome
            self.fields["email"].initial = self.instance.usuario.email

    def clean_senha_atual(self):
        senha = self.cleaned_data.get("senha_atual")
        if not check_password(senha, self.user.password):
            # ISSO AQUI impede que o form seja válido e salva o banco!
            raise forms.ValidationError("A senha atual está incorreta. As alterações não foram salvas.")
        return senha

    @transaction.atomic
    def save(self, commit=True):
        p = super().save(commit=False)
        user = p.usuario
        user.nome = self.cleaned_data["nome"]
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data["email"]
        
        if commit:
            user.save()
            p.save()
        return p