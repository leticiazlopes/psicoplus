from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.models import Sessao

from .forms import SessaoForm


@login_required
def agendamentos_view(request):
    psicologo_perfil = getattr(request.user, "psicologo", None)

    if not psicologo_perfil:
        return redirect("dashboard")

    if request.method == "POST":
        form = SessaoForm(request.POST, psicologo=psicologo_perfil)
        if form.is_valid():
            sessao = form.save(commit=False)
            sessao.psicologo = psicologo_perfil
            sessao.save()
            return redirect("agenda_lista")
    else:
        form = SessaoForm(psicologo=psicologo_perfil)

    lista_sessoes = Sessao.objects.filter(psicologo=psicologo_perfil)

    context = {
        "form": form,
        "sessoes": lista_sessoes,
    }
    return render(request, "agenda/agendamentos_lista.html", context)
