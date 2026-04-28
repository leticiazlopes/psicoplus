from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import CadastroPsicologoView, LoginView

urlpatterns = [
    path("register/psicologo/", CadastroPsicologoView.as_view()),
    path("login/", LoginView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view()),
]