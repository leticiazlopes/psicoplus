from django import forms
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm, UserCreationForm
from django.contrib.auth import get_user_model
from django.db import transaction
from django.contrib.auth.hashers import check_password
from django.utils.translation import gettext_lazy as _

from .models import Usuario, Psicologo
from .models import Paciente
from .models import DiarioPensamento


User = get_user_model()


class LoginUsuarioForm(AuthenticationForm):
    username = forms.EmailField(
        label=_("E-mail"),
        widget=forms.EmailInput(
            attrs={
                "placeholder": _("seu@email.com"),
                "autocomplete": "email",
            }
        ),
    )

    password = forms.CharField(
        label=_("Senha"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": _("Digite sua senha"),
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

        self.fields["password"].widget.attrs.update(
            {
                "class": "w-full rounded-xl border border-slate-200 bg-white py-3 pl-10 pr-10 text-[14px] text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-primary focus:ring-4 focus:ring-primary/10",
            }
        )


class CadastroPsicologoForm(UserCreationForm):
    nome = forms.CharField(
        max_length=255,
        label=_("Nome completo"),
        widget=forms.TextInput(attrs={"placeholder": _("Nome completo")})
    )

    email = forms.EmailField(
        label=_("E-mail"),
        widget=forms.EmailInput(attrs={"placeholder": _("email@exemplo.com")})
    )

    crp = forms.CharField(
        max_length=20,
        label=_("CRP"),
        widget=forms.TextInput(attrs={"placeholder": _("Ex: 13/12345")})
    )

    telefone = forms.CharField(
        required=False,
        label=_("Telefone"),
        widget=forms.TextInput(attrs={"placeholder": _("(83) 99999-9999")})
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
            "placeholder": _("Digite uma senha segura"),
            "class": "w-full rounded-xl border border-slate-200 bg-white px-4 pr-10 py-3 text-[14px] text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-primary focus:ring-4 focus:ring-primary/10"
        })

        self.fields["password2"].widget.attrs.update({
            "placeholder": _("Confirme a senha"),
            "class": "w-full rounded-xl border border-slate-200 bg-white px-4 pr-10 py-3 text-[14px] text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-primary focus:ring-4 focus:ring-primary/10"
        })

    def clean_email(self):
        email = self.cleaned_data["email"]

        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError(_("E-mail já cadastrado."))

        return email

    def clean_crp(self):
        crp = self.cleaned_data["crp"]

        if Psicologo.objects.filter(crp=crp).exists():
            raise forms.ValidationError(_("CRP já cadastrado."))

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
            "aceita_lembrete_email",
        ]
        widgets = {
            "nome_completo": forms.TextInput(attrs={"placeholder": _("Nome completo do paciente")}),
            "email": forms.EmailInput(attrs={"placeholder": _("email@paciente.com")}),
            "telefone": forms.TextInput(attrs={"placeholder": _("(83) 99999-9999")}),
            "data_nascimento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "contato_emergencia_nome": forms.TextInput(attrs={"placeholder": _("Nome do contato")}),
            "contato_emergencia_telefone": forms.TextInput(attrs={"placeholder": _("Telefone de emergência")}),
            "aceita_lembrete_email": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if field.widget.input_type == "checkbox":
                field.widget.attrs.update({
                    "class": "h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary"
                })
            else:
                field.widget.attrs.update({
                    "class": "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-[14px] text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-primary focus:ring-4 focus:ring-primary/10"
                })

    def clean_email(self):
        email = self.cleaned_data.get("email")
        pacientes_com_esse_email = Paciente.objects.filter(email=email)
        
        if self.instance.pk:
            pacientes_com_esse_email = pacientes_com_esse_email.exclude(pk=self.instance.pk)
            
        if pacientes_com_esse_email.exists():
            raise forms.ValidationError(_("Este e-mail já está em uso por outro paciente."))

        usuario_com_esse_email = User.objects.filter(email=email)
        if self.instance.pk and self.instance.usuario_id:
            usuario_com_esse_email = usuario_com_esse_email.exclude(pk=self.instance.usuario_id)

        if usuario_com_esse_email.exists():
            raise forms.ValidationError(_("Este e-mail já está em uso por outro usuário."))
            
        return email

    @transaction.atomic
    def save(self, commit=True):
        paciente = super().save(commit=False)

        if paciente.usuario_id:
            usuario = paciente.usuario
            usuario.nome = paciente.nome_completo
            usuario.email = paciente.email
            usuario.username = paciente.email
        else:
            usuario = User(
                nome=paciente.nome_completo,
                email=paciente.email,
                username=paciente.email,
                perfil=Usuario.Perfil.PACIENTE,
            )
            usuario.set_unusable_password()
        if commit:
            usuario.save()
            paciente.usuario = usuario
            paciente.save()
            self.save_m2m()

        return paciente

class MeuPerfilForm(forms.ModelForm):
    nome = forms.CharField(label=_("Nome completo"))
    email = forms.EmailField(label=_("E-mail"))
    senha_atual = forms.CharField(
        label=_("Senha atual para confirmar"), 
        widget=forms.PasswordInput(attrs={'placeholder': _('Digite sua senha atual')})
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
            raise forms.ValidationError(_("A senha atual está incorreta. As alterações não foram salvas."))
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


class DefinirSenhaPacienteForm(SetPasswordForm):
    error_messages = {
        "password_mismatch": _("As senhas informadas não coincidem."),
    }

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)

        self.fields["new_password1"].label = _("Nova senha")
        self.fields["new_password2"].label = _("Confirme a nova senha")

        self.fields["new_password1"].widget.attrs.update(
            {
                "placeholder": _("Digite uma senha segura"),
                "class": "w-full rounded-[12px] border border-borderSoft bg-white py-3.5 pl-11 pr-12 text-[14.5px] text-slate-900 outline-none transition-all placeholder:text-slate-400 focus:border-primary focus:ring-2 focus:ring-primarySoft",
            }
        )
        self.fields["new_password2"].widget.attrs.update(
            {
                "placeholder": _("Repita a senha"),
                "class": "w-full rounded-[12px] border border-borderSoft bg-white py-3.5 pl-11 pr-12 text-[14.5px] text-slate-900 outline-none transition-all placeholder:text-slate-400 focus:border-primary focus:ring-2 focus:ring-primarySoft",
            }
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.marcar_token_definicao_senha_como_usado()

        if commit:
            user.save()

        return user
class DiarioPensamentoForm(forms.ModelForm):
    class Meta:
        model = DiarioPensamento
        fields = ['situacao', 'emocao_principal', 'intensidade', 'observacoes_livres']
        
    def __init__(self, *xargs, **kwargs):
        super().__init__(*xargs, **kwargs)
        classes_input = "w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 shadow-sm transition focus:border-primary focus:ring-2 focus:ring-primary/30 focus:outline-none"
        
        self.fields['situacao'].widget = forms.Textarea(attrs={
            'class': classes_input,
            'rows': 3,
            'placeholder': _('O que aconteceu?')
        })
        self.fields['emocao_principal'] = forms.CharField(
            required=False,
            label=_("Emoção principal"),
            widget=forms.TextInput(attrs={
                'class': classes_input,
                'placeholder': _('Ex: Ansiedade, Raiva... (Opcional)')
            })
        )
        self.fields['intensidade'].widget = forms.Select(
            choices=[
                (1, _("1 - Muito leve")),
                (2, _("2 - Leve")),
                (3, _("3 - Moderada")),
                (4, _("4 - Intensa")),
                (5, _("5 - Muito intensa")),
            ],
            attrs={'class': classes_input}
        )
        self.fields['observacoes_livres'].widget = forms.Textarea(attrs={
            'class': classes_input,
            'rows': 3,
            'placeholder': _('Como reagiu ao que aconteceu? (Opcional)')
        })
