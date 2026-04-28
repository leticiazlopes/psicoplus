from django.urls import path
from .views import CadastroPsicologoView, LoginUsuarioView, LogoutUsuarioView

urlpatterns = [
    path("cadastro/psicologo/", CadastroPsicologoView.as_view(), name="cadastro_psicologo"),
    path("login/", LoginUsuarioView.as_view(), name="login"),
    path("logout/", LogoutUsuarioView.as_view(), name="logout"),
]