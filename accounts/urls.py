from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views
import django.contrib.auth.views as auth_views
from django.contrib import messages

class MyPasswordChangeView(auth_views.PasswordChangeView):
    def form_valid(self, form):
        # A mensagem é disparada aqui, ANTES do redirecionamento
        messages.success(self.request, "Sua senha foi alterada com sucesso!")
        return super().form_valid(form)

urlpatterns = [
    path("psicologos/", views.PsicologoListView.as_view(), name="psicologos"),
    path("psicologos/cadastrar/", views.CadastroPsicologoView.as_view(), name="cadastro_psicologo"),
    path('meu-perfil/', views.MeuPerfilUpdateView.as_view(), name='meu_perfil'),
    path(
        'alterar-senha/', 
        MyPasswordChangeView.as_view(
            template_name='accounts/alterar_senha.html',
            success_url=reverse_lazy('pacientes_lista')
        ), 
        name='password_change'
    ),
    path("login/", views.LoginUsuarioView.as_view(), name="login"),
    path("logout/", views.LogoutUsuarioView.as_view(), name="logout"),
    path("definir-senha/<uuid:token>/", views.DefinirSenhaPacienteView.as_view(), name="definir_senha_paciente"),
    path("pacientes/", views.PacienteListView.as_view(), name="pacientes_lista"),
    path("pacientes/<uuid:pk>/", views.PacienteDetailView.as_view(), name="paciente_perfil"),
    path("pacientes/cadastrar/", views.CadastroPacienteView.as_view(), name="cadastro_paciente"),
    path("pacientes/<uuid:pk>/inativar/", views.inativar_paciente, name="inativar_paciente"),
    path("pacientes/<uuid:pk>/ativar/", views.ativar_paciente, name="ativar_paciente"),
    path("pacientes/<uuid:pk>/editar/", views.PacienteUpdateView.as_view(), name="editar_paciente"),
    path("esqueci-senha/", views.esqueci_senha_request, name="esqueci_senha"),
    path("validar-codigo/", views.validar_codigo_e_salvar, name="validar_codigo"),
    path("paciente/dashboard/", views.dashboard_paciente_page, name="dashboard_paciente"),
    path("api/paciente/home/", views.api_paciente_home, name="api_paciente_home"),
    ]   
