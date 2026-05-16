from django.views.generic import CreateView, ListView, UpdateView
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from .forms import CadastroPacienteForm, CadastroPsicologoForm, LoginUsuarioForm, MeuPerfilForm
from .models import Psicologo
from .models import Paciente
from .models import Usuario
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.contrib.messages.views import SuccessMessageMixin
import random
import datetime
from django.utils import timezone
from django.core.mail import send_mail




class PsicologoListView(LoginRequiredMixin, ListView):
    template_name = "accounts/psicologos_lista.html"
    model = Psicologo
    context_object_name = "psicologos"
    login_url = reverse_lazy("login")

    def get_queryset(self):
        return (
            Psicologo.objects.select_related("usuario")
            .order_by("usuario__nome")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        psicologos = context["psicologos"]

        context["psicologos_ativos"] = sum(1 for psicologo in psicologos if psicologo.ativo)
        context["psicologos_inativos"] = sum(1 for psicologo in psicologos if not psicologo.ativo)
        return context

class CadastroPsicologoView(CreateView):
    template_name = "accounts/cadastro_psicologo.html"
    form_class = CadastroPsicologoForm
    success_url = reverse_lazy("login")
    def form_valid(self, form):
        messages.success(self.request, "Sua conta foi criada com sucesso! Faça login para começar.")
        return super().form_valid(form)
    
class MeuPerfilUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Psicologo
    form_class = MeuPerfilForm
    template_name = "accounts/meu_perfil.html"
    success_url = reverse_lazy("pacientes_lista")
    success_message = "Seu perfil foi atualizado com sucesso!"

    def get_object(self, queryset=None):
        return get_object_or_404(Psicologo, usuario=self.request.user)

    def get_form_kwargs(self):
        # Garante que o formulário saiba quem é o usuário para validar e-mails duplicados, etc.
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

class LoginUsuarioView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    authentication_form = LoginUsuarioForm

    def get_success_url(self):
        user = self.request.user
        if user.perfil == Usuario.Perfil.PSICOLOGO:
            return reverse_lazy("pacientes_lista")
        
@method_decorator(require_POST, name='dispatch')
class LogoutUsuarioView(LogoutView):
    next_page = reverse_lazy("login")

    def post(self, request, *args, **kwargs):
        """
        Sobrescrevemos o post para adicionar a mensagem de sucesso 
        antes de processar o encerramento da sessão.
        """
        messages.success(request, "Logout realizado com sucesso.")
        return super().post(request, *args, **kwargs)

class CadastroPacienteView(LoginRequiredMixin, CreateView):
    model = Paciente
    template_name = "accounts/cadastro_paciente.html"
    form_class = CadastroPacienteForm 
    success_url = reverse_lazy("pacientes_lista")
    def form_valid(self, form):
        form.instance.psicologo = self.request.user.psicologo
        messages.success(self.request, "Paciente cadastrado com sucesso!")
        return super().form_valid(form)

class PacienteListView(LoginRequiredMixin, ListView):
    model = Paciente
    template_name = "accounts/pacientes_lista.html"
    context_object_name = "pacientes"
    def get_queryset(self):
        queryset = Paciente.objects.filter(psicologo=self.request.user.psicologo)
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(nome_completo__icontains=search_query)
        return queryset.order_by('nome_completo')

class PacienteUpdateView(LoginRequiredMixin, UpdateView):
    model = Paciente
    form_class = CadastroPacienteForm
    template_name = "accounts/cadastro_paciente.html"
    success_url = reverse_lazy("pacientes_lista")
    def get_queryset(self):
        return Paciente.objects.filter(psicologo=self.request.user.psicologo)

    def form_valid(self, form):
        messages.success(self.request, "Alterações salvas com sucesso!")
        return super().form_valid(form)

def inativar_paciente(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk, psicologo=request.user.psicologo)
    paciente.ativo = False
    paciente.save()
    messages.success(request, "Paciente inativado com sucesso.")
    return redirect("pacientes_lista")

def ativar_paciente(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk, psicologo=request.user.psicologo)
    paciente.ativo = True
    paciente.save()
    messages.success(request, "Paciente ativado com sucesso.")  
    return redirect("pacientes_lista")

def esqueci_senha_request(request):
    """Passo 1: Recebe o e-mail, gera o código de 6 dígitos e faz o disparo real"""
    if request.method == "POST":
        email_digitado = request.POST.get("email")
        
        # Como o seu USERNAME_FIELD é o email, buscamos direto por ele
        user = Usuario.objects.filter(email=email_digitado).first()
        
        # Segurança (LGPD): Evita revelar se o e-mail existe ou não na base de dados
        if user:
            # Gera um código aleatório de 6 dígitos (ex: '482910')
            codigo = f"{random.randint(100000, 999999)}"
            
            # Define a expiração para daqui a 15 minutos
            user.codigo_recuperacao = codigo
            user.codigo_expiracao = timezone.now() + datetime.timedelta(minutes=15)
            user.save()
            
            # Corpo do e-mail estilizado com HTML, parecido com o do seu amigo
            html_message = f"""
            <div style="background-color: #ffffff; font-family: Arial, sans-serif; padding: 30px; border-radius: 8px; max-width: 500px; margin: 0 auto; border: 1px solid #e0e0e0; color: #333333;">
                <h2 style="color: #4A90E2; margin-top: 0;">Recuperação de Acesso - Psico+</h2>
                <p>Olá <b>{user.nome}</b>,</p>
                <p>Recebemos uma solicitação de redefinição de senha para a sua conta de {user.get_perfil_display()}.</p>
                <p>Utilize o código de autorização abaixo para cadastrar uma nova senha:</p>
                
                <div style="background-color: #f4f6f9; padding: 15px; text-align: center; font-size: 28px; font-weight: bold; letter-spacing: 6px; color: #4A90E2; border-radius: 6px; margin: 20px 0; border: 1px dashed #4A90E2;">
                    {codigo}
                </div>
                
                <p style="color: #d9534f; font-size: 13px; font-weight: bold;">⚠️ Atenção: Este código é válido por 15 minutos.</p>
                <p style="color: #777777; font-size: 12px; margin-top: 25px; border-top: 1px solid #eeeeee; padding-top: 15px;">Se você não solicitou essa redefinição, nenhuma ação é necessária. Sua senha continuará segura.</p>
            </div>
            """
            
            # Dispara o e-mail usando o SMTP do seu settings.py (Gmail)
            send_mail(
                subject="[Psico+] Código de Recuperação de Senha",
                message=f"Seu código de recuperação é: {codigo}", # Fallback em texto puro
                from_email=None,
                recipient_list=[user.email],
                html_message=html_message
            )
            
        # Guarda o e-mail temporariamente na sessão do navegador do usuário
        # Isso serve para que a próxima página saiba qual usuário estamos alterando
        request.session['email_recuperacao'] = email_digitado
        return redirect('validar_codigo')

    return render(request, "auth/password_reset.html")


def validar_codigo_e_salvar(request):
    """Passo 2: Valida o código digitado e atualiza a senha de forma segura"""
    email = request.session.get('email_recuperacao')
    
    # Se o usuário tentar acessar a URL de confirmação direto sem passar pelo e-mail, barra ele
    if not email:
        return redirect('esqueci_senha_request')

    if request.method == "POST":
        codigo_digitado = request.POST.get("codigo")
        nova_senha = request.POST.get("nova_senha")
        
        user = Usuario.objects.filter(email=email).first()
        
        if user and user.codigo_recuperacao == codigo_digitado:
            # Verifica se o código não expirou no tempo
            if timezone.now() < user.codigo_expiracao:
                # O método set_password() do Django já aplica a criptografia PBKDF2 automaticamente
                user.set_password(nova_senha)
                
                # Reseta os campos para que o código não possa ser usado uma segunda vez
                user.codigo_recuperacao = None
                user.codigo_expiracao = None
                user.save()
                
                # Limpa a sessão
                del request.session['email_recuperacao']
                
                messages.success(request, "Senha alterada com sucesso! Faça seu login.")
                return redirect('login') # Ajuste para a sua rota de login
            else:
                messages.error(request, "Este código já expirou. Solicite um novo.")
        else:
            messages.error(request, "Código de verificação incorreto.")

    return render(request, "auth/password_reset_confirm.html")