from django.urls import path

from . import views

urlpatterns = [
    path("atendimentos/", views.atendimentos_view, name="atendimentos_lista"),
    path("api/prontuarios/", views.criar_prontuario_api, name="criar_prontuario_api"),
    path("api/prontuarios/<uuid:prontuario_id>/", views.editar_prontuario_api, name="editar_prontuario_api"),
]
