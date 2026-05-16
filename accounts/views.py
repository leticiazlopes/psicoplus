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
from django.contrib.auth.decorators import login_required




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
            return reverse_lazy("dashboard")
        return reverse_lazy("dashboard")
        
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
        
        
        status_filtro = self.request.GET.get('status')
        if status_filtro == 'ativos':
            queryset = queryset.filter(ativo=True)
        elif status_filtro == 'inativos':
            queryset = queryset.filter(ativo=False)

        
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(nome_completo__icontains=search_query)
            
        return queryset.order_by('nome_completo')

    def get_context_data(self, **kwargs):
        
        context = super().get_context_data(**kwargs)
        psicologo_logado = self.request.user.psicologo

        
        context["total_pacientes"] = Paciente.objects.filter(psicologo=psicologo_logado).count()
        context["total_ativos"] = Paciente.objects.filter(psicologo=psicologo_logado, ativo=True).count()
        context["total_inativos"] = Paciente.objects.filter(psicologo=psicologo_logado, ativo=False).count()
        
        
        context["status_filtro"] = self.request.GET.get('status')
        
        return context
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
        
        
        user = Usuario.objects.filter(email=email_digitado).first()
        
        
        if user:
            
            codigo = f"{random.randint(100000, 999999)}"
            
            
            user.codigo_recuperacao = codigo
            user.codigo_expiracao = timezone.now() + datetime.timedelta(minutes=15)
            user.save()
            
            
            
            html_message = f"""
            <div style="background-color: 
                <div style="background-color: 
                    
                    <h2 style="color: 
                        Recuperação de Acesso — Psico+
                    </h2>
                    
                    <p style="font-size: 15px; line-height: 1.6; color: 
                    <p style="font-size: 15px; line-height: 1.6; color: 
                    <p style="font-size: 15px; line-height: 1.6; color: 
                    
                    <div style="background-color: 
                        {codigo}
                    </div>
                    
                    <p style="color: 
                        ⚠️ Atenção: Este código é válido por 15 minutos.
                    </p>
                    
                    <p style="color: 
                        Se você não solicitou essa redefinição, nenhuma ação é necessária. Sua senha atual continuará segura e seu acesso protegido.
                    </p>
                </div>
            </div>
            """
            
            
            send_mail(
                subject="[Psico+] Código de Recuperação de Senha",
                message=f"Seu código de recuperação é: {codigo}", 
                from_email=None,
                recipient_list=[user.email],
                html_message=html_message
            )
            
        
        
        request.session['email_recuperacao'] = email_digitado
        return redirect('validar_codigo')

    return render(request, "auth/password_reset.html")


def validar_codigo_e_salvar(request):
    """Passo 2: Valida o código digitado e atualiza a senha de forma segura"""
    email = request.session.get('email_recuperacao')
    
    
    if not email:
        return redirect('esqueci_senha_request')

    if request.method == "POST":
        codigo_digitado = request.POST.get("codigo")
        nova_senha = request.POST.get("nova_senha")
        
        user = Usuario.objects.filter(email=email).first()
        
        if user and user.codigo_recuperacao == codigo_digitado:
            
            if timezone.now() < user.codigo_expiracao:
                
                user.set_password(nova_senha)
                
                
                user.codigo_recuperacao = None
                user.codigo_expiracao = None
                user.save()
                
                
                del request.session['email_recuperacao']
                
                messages.success(request, "Senha alterada com sucesso! Faça seu login.")
                return redirect('login') 
            else:
                messages.error(request, "Este código já expirou. Solicite um novo.")
        else:
            messages.error(request, "Código de verificação incorreto.")

    return render(request, "auth/password_reset_confirm.html")

@login_required
def dashboard_view(request):
    
    try:
        psicologo_logado = request.user.psicologo
        
        
        pacientes_ativos = Paciente.objects.filter(
            psicologo=psicologo_logado, 
            ativo=True
        ).count()
        
    except AttributeError:
        
        pacientes_ativos = 0

    
    context = {
        'sessoes_hoje': 0,        
        'sessoes_mes': 0,         
        'pacientes_ativos': pacientes_ativos, 
        'valor_pendente': "0,00",  
        'proximas_sessoes': [],   
    }
    
    return render(request, 'accounts/dashboard.html', context)