from django.urls import path
from .views import CadastroPsicologoView, LoginUsuarioView

urlpatterns = [
    path("cadastro/psicologo/", CadastroPsicologoView.as_view(), name="cadastro_psicologo"),
    path("login/", LoginUsuarioView.as_view(), name="login"),
]