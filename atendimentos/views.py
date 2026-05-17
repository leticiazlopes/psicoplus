from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def atendimentos_view(request):
    return render(request, "atendimentos/lista.html")
