from django.urls import path
from .views import CadastroPsicologoView

urlpatterns = [
    path("register/psicologo/", CadastroPsicologoView.as_view(), name="cadastro_psicologo"),
]