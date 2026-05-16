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
        # 1. Começamos pegando a base filtrada pelo psicólogo logado
        queryset = Paciente.objects.filter(psicologo=self.request.user.psicologo)
        
        # 2. CAPTURA DO CARD: Verifica se o usuário clicou em Ativos ou Inativos
        status_filtro = self.request.GET.get('status')
        if status_filtro == 'ativos':
            queryset = queryset.filter(ativo=True)
        elif status_filtro == 'inativos':
            queryset = queryset.filter(ativo=False)

        # 3. MANTÉM A SUA BUSCA POR TEXTO: Se digitaram algo na barra de pesquisa
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(nome_completo__icontains=search_query)
            
        return queryset.order_by('nome_completo')

    def get_context_data(self, **kwargs):
        # Puxa o contexto padrão do Django
        context = super().get_context_data(**kwargs)
        psicologo_logado = self.request.user.psicologo

        # 4. ALIMENTA OS CARDS: Faz as contagens reais no banco de dados
        context["total_pacientes"] = Paciente.objects.filter(psicologo=psicologo_logado).count()
        context["total_ativos"] = Paciente.objects.filter(psicologo=psicologo_logado, ativo=True).count()
        context["total_inativos"] = Paciente.objects.filter(psicologo=psicologo_logado, ativo=False).count()
        
        # 5. ENVIA O FILTRO PRO HTML: Para acender a borda do card selecionado
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
            <div style="background-color: #f8fafc; padding: 40px 10px; font-family: 'Segoe UI', Arial, sans-serif;">
                <div style="background-color: #ffffff; padding: 35px; border-radius: 16px; max-width: 500px; margin: 0 auto; box-shadow: 0 4px 12px rgba(0,0,0,0.03); border: 1px solid #f1f5f9; color: #1e293b;">
                    
                    <h2 style="color: #6d4aff; font-size: 22px; font-weight: 700; margin-top: 0; margin-bottom: 20px; display: flex; align-items: center; gap: 8px;">
                        Recuperação de Acesso — Psico+
                    </h2>
                    
                    <p style="font-size: 15px; line-height: 1.6; color: #334155;">Olá, <b style="color: #0f172a;">{user.nome}</b>.</p>
                    <p style="font-size: 15px; line-height: 1.6; color: #334155;">Recebemos uma solicitação de redefinição de senha para a sua conta de <b>{user.get_perfil_display()}</b>.</p>
                    <p style="font-size: 15px; line-height: 1.6; color: #334155;">Utilize o código de autorização abaixo para cadastrar sua nova senha:</p>
                    
                    <div style="background-color: #f8fafc; padding: 18px; text-align: center; font-size: 32px; font-weight: 800; letter-spacing: 6px; color: #6d4aff; border-radius: 12px; margin: 25px 0; border: 2px dashed #e2e8f0;">
                        {codigo}
                    </div>
                    
                    <p style="color: #ef4444; font-size: 13px; font-weight: 600; margin-bottom: 25px; display: flex; align-items: center; gap: 5px;">
                        ⚠️ Atenção: Este código é válido por 15 minutos.
                    </p>
                    
                    <p style="color: #94a3b8; font-size: 12px; line-height: 1.5; margin-top: 30px; border-top: 1px solid #f1f5f9; padding-top: 20px;">
                        Se você não solicitou essa redefinição, nenhuma ação é necessária. Sua senha atual continuará segura e seu acesso protegido.
                    </p>
                </div>
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

@login_required
def dashboard_view(request):
    # 1. Pegamos a instância de Psicologo do usuário logado através do related_name
    try:
        psicologo_logado = request.user.psicologo
        
        # 2. Buscamos os pacientes vinculados a ESSE psicólogo que estejam ativos (ativo=True)
        pacientes_ativos = Paciente.objects.filter(
            psicologo=psicologo_logado, 
            ativo=True
        ).count()
        
    except AttributeError:
        # Caso seja um usuário administrador ou alguém sem o perfil de Psicólogo criado
        pacientes_ativos = 0

    # 3. Montamos o contexto para alimentar o HTML
    context = {
        'sessoes_hoje': 0,        # Fictício por enquanto
        'sessoes_mes': 0,         # Fictício por enquanto
        'pacientes_ativos': pacientes_ativos, # 100% REAL E DINÂMICO! 🚀
        'valor_pendente': "0,00",  # Fictício por enquanto
        'proximas_sessoes': [],   # Lista vazia por enquanto
    }
    
    return render(request, 'accounts/dashboard.html', context)