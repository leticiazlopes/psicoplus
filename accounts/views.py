from django.views.generic import CreateView
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.contrib import messages

from .forms import CadastroPsicologoForm


class CadastroPsicologoView(CreateView):
    template_name = "accounts/cadastro_psicologo.html"
    form_class = CadastroPsicologoForm
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        messages.success(self.request, "Cadastro realizado com sucesso.")
        return super().form_valid(form)
    

class LoginUsuarioView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user

        if user.perfil == "psicologo":
            return reverse_lazy("cadastro_psicologo")

        if user.perfil == "paciente":
            return ...

        return reverse_lazy("login")

class LogoutUsuarioView(LogoutView):
    next_page = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        messages.success(request, "Logout realizado com sucesso.")
        return super().dispatch(request, *args, **kwargs)