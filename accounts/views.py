from django.views.generic import CreateView, FormView, ListView, UpdateView
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from .forms import CadastroPacienteForm, CadastroPsicologoForm, DefinirSenhaPacienteForm, LoginUsuarioForm, MeuPerfilForm
from .models import Usuario, Psicologo, Paciente, Sessao
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.contrib.messages.views import SuccessMessageMixin
import random
import datetime
from django.utils import timezone
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from django.views.generic import FormView
from django.urls import reverse_lazy
from django.contrib import messages
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

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.perfil == Usuario.Perfil.PACIENTE:
            if request.method != "GET":
                return redirect("meu_perfil")

            paciente = get_object_or_404(
                Paciente.objects.select_related("usuario", "psicologo__usuario"),
                usuario=request.user,
            )
            context = {
                "perfil_tipo": "paciente",
                "paciente": paciente,
                "usuario_logado": request.user,
            }
            return render(request, self.template_name, context)

        return super().dispatch(request, *args, **kwargs)

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

        if user.perfil == Usuario.Perfil.PACIENTE:
            return reverse_lazy("dashboard_paciente")

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


class DefinirSenhaPacienteView(FormView):
    template_name = "auth/definir_senha_paciente.html"
    form_class = DefinirSenhaPacienteForm
    success_url = reverse_lazy("login")
    usuario = None
    _token_valido_cache = False  # Cache interno para o estado do token

    def dispatch(self, request, *args, **kwargs):
        uidb64 = self.kwargs.get("uid")
        token = self.kwargs.get("token")
        
        try:
            # 1. Decodifica o UID com segurança para obter a chave primária real (UUID ou ID)
            uid = force_str(urlsafe_base64_decode(uidb64))
            self.usuario = Usuario.objects.filter(pk=uid, perfil=Usuario.Perfil.PACIENTE).first()
        except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
            self.usuario = None

        # 2. Valida o token gerado pelo generator oficial do Django
        if self.usuario and default_token_generator.check_token(self.usuario, token):
            self._token_valido_cache = True
        else:
            self._token_valido_cache = False

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.usuario
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["token_valido"] = self.token_valido
        context["mensagem_token"] = self.mensagem_token
        context["paciente_email"] = self.usuario.email if self.usuario else None
        return context

    @property
    def token_valido(self):
        return self._token_valido_cache

    @property
    def mensagem_token(self):
        if not self.usuario or not self._token_valido_cache:
            return "Este link de definição de senha é inválido ou já expirou (prazo de 48 horas)."
        return ""

    def get(self, request, *args, **kwargs):
        if not self.token_valido:
            messages.error(request, self.mensagem_token)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not self.token_valido:
            messages.error(request, self.mensagem_token)
            return self.render_to_response(self.get_context_data(form=None))
        return super().post(request, *args, **kwargs)

    def get_form(self, form_class=None):
        if not self.token_valido:
            return None
        return super().get_form(form_class)

    def form_valid(self, form):
        # Altera a senha usando o método correto de hash do Django
        nova_senha = form.cleaned_data.get('nova_senha') or self.request.POST.get('senha')
        if nova_senha:
            self.usuario.set_password(nova_senha)
            self.usuario.save()
            messages.success(self.request, "Senha definida com sucesso! Agora você já pode fazer login.")
        else:
            form.save()
            messages.success(self.request, "Senha definida com sucesso! Agora você já pode fazer login.")
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

    hoje = timezone.now().date()
    sessoes_futuras = Sessao.objects.filter(paciente=paciente, data__gte=hoje).exclude(status=Sessao.Status.CANCELADA)
    sessoes_futuras.update(status=Sessao.Status.CANCELADA)

    messages.success(request, "Paciente inativado com sucesso. Sessões futuras foram canceladas.")
    return redirect("pacientes_lista")

def ativar_paciente(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk, psicologo=request.user.psicologo)
    paciente.ativo = True
    paciente.save()


    hoje = timezone.now().date()
    sessoes_futuras_canceladas = Sessao.objects.filter(paciente=paciente, data__gt=hoje, status=Sessao.Status.CANCELADA)
    sessoes_futuras_canceladas.update(status=Sessao.Status.PENDENTE)

    messages.success(request, "Paciente ativado com sucesso. Sessões futuras reativadas.")
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
            
            
            
          # Código HTML corrigido e com os estilos fechados corretamente
            html_message = f"""
            <div style="background-color: #f7f5ff; padding: 30px; font-family: sans-serif;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 20px; border: 1px solid #e7e9f2;">
                    
                    <h2 style="color: #1e293b; font-size: 24px; margin-top: 0;">
                        Recuperação de Acesso — Psico+
                    </h2>
                    
                    <p style="font-size: 15px; line-height: 1.6; color: #475569;">
                        Olá,
                    </p>
                    <p style="font-size: 15px; line-height: 1.6; color: #475569;">
                        Recebemos uma solicitação para redefinir a senha da sua conta no sistema <strong>Psico+</strong>. Utilize o código de verificação abaixo para prosseguir:
                    </p>
                    
                    <div style="background-color: #eee9ff; color: #6d4aff; font-size: 32px; font-weight: bold; text-align: center; padding: 20px; border-radius: 12px; margin: 25px 0; letter-spacing: 5px;">
                        {codigo}
                    </div>
                    
                    <p style="color: #ef4444; font-size: 14px; font-weight: bold;">
                        ⚠️ Atenção: Este código é válido por 15 minutos.
                    </p>
                    
                    <p style="color: #64748b; font-size: 13px; line-height: 1.6; margin-bottom: 0; border-top: 1px solid #f1f5f9; padding-top: 20px;">
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

   
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required

@login_required
def api_paciente_home(request):
    """
    [US-10] Endpoint GET /api/paciente/home/
    Subtask: Endpoint acessível APENAS para usuários com tipo=paciente
    """
    if request.user.perfil != Usuario.Perfil.PACIENTE:
        return JsonResponse({"error": "Acesso proibido. Endpoint restrito a pacientes."}, status=403)
        
    paciente_perfil = getattr(request.user, "paciente", None)
    if not paciente_perfil:
        return JsonResponse({"error": "Perfil de paciente não encontrado."}, status=404)

    agora = timezone.now()
    proxima_sessao = Sessao.objects.filter(
        paciente=paciente_perfil,
        data__gte=agora.date(),
    ).exclude(
        status=Sessao.Status.CANCELADA
    ).order_by("data", "horario_inicio").first()

    if proxima_sessao and proxima_sessao.data == agora.date():
        if proxima_sessao.horario_inicio < agora.time():
            proxima_sessao = Sessao.objects.filter(
                paciente=paciente_perfil,
                data__gt=agora.date()
            ).exclude(status=Sessao.Status.CANCELADA).order_by("data", "horario_inicio").first()

    if proxima_sessao:
        dados_sessao = {
            "tem_sessao": True,
            "data": proxima_sessao.data.strftime("%d/%m/%Y"),
            "horario": proxima_sessao.horario_inicio.strftime("%H:%M"),
            "status": proxima_sessao.get_status_display(),
            "plano": proxima_sessao.atendido_por_plano
        }
    else:
        dados_sessao = {
            "tem_sessao": False
        }

    return JsonResponse(dados_sessao)


@login_required
def dashboard_paciente_page(request):
    if request.user.perfil != Usuario.Perfil.PACIENTE:
        return HttpResponseForbidden("Você não tem permissão para acessar esta área.")
        
    return render(request, "accounts/dashboard_paciente.html")

@login_required
def inicio_view(request):
    if request.user.perfil == Usuario.Perfil.PACIENTE:
        return redirect("dashboard_paciente")
    return render(request, "agenda/agendamentos_lista.html")