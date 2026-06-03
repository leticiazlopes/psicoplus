from django.urls import path

from . import views

urlpatterns = [
    path("atendimentos/", views.atendimentos_view, name="atendimentos_lista"),
    path("api/prontuarios/", views.criar_prontuario_api, name="criar_prontuario_api"),
]
