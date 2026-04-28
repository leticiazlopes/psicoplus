from django.urls import path
from .views import CadastroPsicologoView

urlpatterns = [
    path("cadastro/", CadastroPsicologoView.as_view(), name="cadastro_psicologo"),
]