from django.views.generic import CreateView
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