from django.urls import path
from .views import CadastroPsicologoView, LoginUsuarioView, LogoutUsuarioView, PsicologoListView

urlpatterns = [
    path("psicologos/", PsicologoListView.as_view(), name="psicologos"),
    path("psicologos/cadastrar/", CadastroPsicologoView.as_view(), name="cadastro_psicologo"),
    path("login/", LoginUsuarioView.as_view(), name="login"),
    path("logout/", LogoutUsuarioView.as_view(), name="logout"),
]
