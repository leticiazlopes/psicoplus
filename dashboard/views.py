import datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from accounts.models import Paciente, Sessao


@login_required
def dashboard_view(request):
    try:
        psicologo_logado = request.user.psicologo

        # 1. Datas de referência baseadas no timezone configurado
        hoje = timezone.localtime(timezone.now()).date()
        inicio_mes = hoje.replace(day=1)

        # 2. Pacientes Ativos
        pacientes_ativos = Paciente.objects.filter(
            psicologo=psicologo_logado,
            ativo=True,
        ).count()

        # 3. Métricas de Sessões (Hoje e Mês)
        sessoes_hoje = Sessao.objects.filter(
            psicologo=psicologo_logado,
            data=hoje,
        ).count()

        fim_mes = (
            hoje.replace(month=hoje.month % 12 + 1, day=1) - datetime.timedelta(days=1)
            if hoje.month == 12
            else hoje.replace(month=hoje.month + 1, day=1) - datetime.timedelta(days=1)
        )
        sessoes_mes_queryset = Sessao.objects.filter(
            psicologo=psicologo_logado,
            data__gte=inicio_mes,
            data__lte=fim_mes,
        )
        # Nota: O filtro acima pega do dia 1 até o último dia do mês corrente de forma segura.
        sessoes_mes = sessoes_mes_queryset.count()

        # 4. Faturamento/Valor total do mês corrente
        faturamento_mes = (
            sessoes_mes_queryset.aggregate(total=Sum("valor"))["total"] or 0.00
        )
        valor_mes_formatado = (
            f"{faturamento_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

        # 5. Próximas 5 sessões agendadas a partir de hoje
        proximas_sessoes = (
            Sessao.objects.filter(
                psicologo=psicologo_logado,
                data__gte=hoje,
            )
            .select_related("paciente")
            .order_by("data", "horario_inicio")[:5]
        )
    except AttributeError:
        # Fallback caso um administrador ou usuário sem perfil de psicólogo acesse
        sessoes_hoje = 0
        sessoes_mes = 0
        pacientes_ativos = 0
        valor_mes_formatado = "0,00"
        proximas_sessoes = []

    context = {
        "sessoes_hoje": sessoes_hoje,
        "sessoes_mes": sessoes_mes,
        "pacientes_ativos": pacientes_ativos,
        "valor_pendente": valor_mes_formatado,
        "proximas_sessoes": proximas_sessoes,
    }
    return render(request, "dashboard/home.html", context)
