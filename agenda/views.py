from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_date

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
    data_filtro = request.GET.get("data")

    if data_filtro:
        data_selecionada = parse_date(data_filtro)
        if data_selecionada:
            lista_sessoes = lista_sessoes.filter(data=data_selecionada)

    context = {
        "form": form,
        "sessoes": lista_sessoes,
        "data_filtro": data_filtro or "",
    }
    return render(request, "agenda/agendamentos_lista.html", context)
