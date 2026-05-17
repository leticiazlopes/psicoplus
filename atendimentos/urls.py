from django.urls import path

from . import views

urlpatterns = [
    path("atendimentos/", views.atendimentos_view, name="atendimentos_lista"),
]
