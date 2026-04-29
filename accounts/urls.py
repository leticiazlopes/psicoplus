from django.urls import path
from .views import CadastroPsicologoView, LoginUsuarioView, LogoutUsuarioView, PsicologoListView, CadastroPacienteView, PacienteListView, inativar_paciente, PacienteUpdateView

urlpatterns = [
    path("psicologos/", PsicologoListView.as_view(), name="psicologos"),
    path("psicologos/cadastrar/", CadastroPsicologoView.as_view(), name="cadastro_psicologo"),
    path("login/", LoginUsuarioView.as_view(), name="login"),
    path("logout/", LogoutUsuarioView.as_view(), name="logout"),
    path("pacientes/", PacienteListView.as_view(), name="pacientes_lista"),
    path("pacientes/cadastrar/", CadastroPacienteView.as_view(), name="cadastro_paciente"),
    path("pacientes/<uuid:pk>/inativar/", inativar_paciente, name="inativar_paciente"),
    path("pacientes/<uuid:pk>/editar/", PacienteUpdateView.as_view(), name="editar_paciente"),
]
