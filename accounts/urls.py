from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from .views import CadastroPsicologoView, LoginUsuarioView, LogoutUsuarioView, MeuPerfilUpdateView, PsicologoListView, CadastroPacienteView, PacienteListView, inativar_paciente, ativar_paciente, PacienteUpdateView
import django.contrib.auth.views as auth_views
from django.contrib import messages

class MyPasswordChangeView(auth_views.PasswordChangeView):
    def form_valid(self, form):
        # A mensagem é disparada aqui, ANTES do redirecionamento
        messages.success(self.request, "Sua senha foi alterada com sucesso!")
        return super().form_valid(form)

urlpatterns = [
    path("psicologos/", PsicologoListView.as_view(), name="psicologos"),
    path("psicologos/cadastrar/", CadastroPsicologoView.as_view(), name="cadastro_psicologo"),
    path('meu-perfil/', MeuPerfilUpdateView.as_view(), name='meu_perfil'),
    path(
        'alterar-senha/', 
        MyPasswordChangeView.as_view(
            template_name='accounts/alterar_senha.html',
            success_url=reverse_lazy('pacientes_lista')
        ), 
        name='password_change'
    ),
    path("login/", LoginUsuarioView.as_view(), name="login"),
    path("logout/", LogoutUsuarioView.as_view(), name="logout"),
    path("pacientes/", PacienteListView.as_view(), name="pacientes_lista"),
    path("pacientes/cadastrar/", CadastroPacienteView.as_view(), name="cadastro_paciente"),
    path("pacientes/<uuid:pk>/inativar/", inativar_paciente, name="inativar_paciente"),
    path("pacientes/<uuid:pk>/ativar/", ativar_paciente, name="ativar_paciente"),
    path("pacientes/<uuid:pk>/editar/", PacienteUpdateView.as_view(), name="editar_paciente"),
]
