from django.urls import path

from . import views

urlpatterns = [
    path("agenda/", views.agendamentos_view, name="agenda_lista"),
    path("agenda/editar/<uuid:sessao_id>/", views.editar_sessao_view, name="editar_sessao"),
    path("agenda/cancelar/<uuid:sessao_id>/", views.cancelar_sessao_view, name="cancelar_sessao"),
]
