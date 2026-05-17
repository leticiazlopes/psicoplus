from django.urls import path

from . import views

urlpatterns = [
    path("inicio/", views.dashboard_view, name="dashboard"),
]
