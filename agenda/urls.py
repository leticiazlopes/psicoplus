from django.urls import path

from . import views

urlpatterns = [
    path("agenda/", views.agendamentos_view, name="agenda_lista"),
]
