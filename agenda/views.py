import calendar
import datetime
from urllib.parse import parse_qs, urlparse

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.utils import timezone

from accounts.models import SerieSessao, Sessao

from .forms import SessaoForm

import json
from django.http import JsonResponse
from accounts.models import HistoricoStatusSessao
from django.views.decorators.http import require_POST

def _get_data_filtro(request):
    data_filtro = request.GET.get("data")
    if data_filtro:
        return data_filtro

    return_to = request.POST.get("return_to", "")
    if not return_to:
        return ""

    return parse_qs(urlparse(return_to).query).get("data", [""])[0]


def _get_redirect_destino(request):
    return_to = request.POST.get("return_to") or request.GET.get("return_to")
    if return_to and return_to.startswith("/"):
        return return_to

    data_filtro = _get_data_filtro(request)
    if data_filtro:
        return f"/agenda/?data={data_filtro}"

    return "agenda_lista"


def _criar_sessao_ou_serie(psicologo_perfil, form):
    sessao = form.save(commit=False)
    sessao.psicologo = psicologo_perfil

    repeticoes = form.cleaned_data.get("repeticoes")
    if not repeticoes:
        sessao.save()
        return

    serie = SerieSessao.objects.create(
        psicologo=psicologo_perfil,
        paciente=sessao.paciente,
    )

    sessoes = []
    for indice in range(repeticoes):
        data_sessao = sessao.data + datetime.timedelta(days=7 * indice)
        sessoes.append(
            Sessao(
                psicologo=psicologo_perfil,
                paciente=sessao.paciente,
                serie=serie,
                posicao_na_serie=indice + 1,
                data=data_sessao,
                horario_inicio=sessao.horario_inicio,
                duracao_minutos=sessao.duracao_minutos,
                valor=sessao.valor,
                status=sessao.status,
                atendido_por_plano=sessao.atendido_por_plano,
                isento_pagamento=sessao.isento_pagamento,
            )
        )

    Sessao.objects.bulk_create(sessoes)


def _build_sessoes_queryset(psicologo_perfil):
    return (
        Sessao.objects.filter(psicologo=psicologo_perfil)
        .select_related("paciente", "serie")
        .annotate(total_sessoes_serie=Count("serie__sessoes"))
    )


def _get_sessoes_ativas_da_serie(sessao):
    return (
        Sessao.objects.filter(serie=sessao.serie)
        .exclude(status=Sessao.Status.CANCELADA)
        .order_by("posicao_na_serie", "data", "horario_inicio")
    )


def _get_sessoes_ativas_a_partir_da_atual(sessao):
    posicao_referencia = sessao.posicao_na_serie or 1
    return (
        _get_sessoes_ativas_da_serie(sessao)
        .filter(posicao_na_serie__gte=posicao_referencia)
    )


@transaction.atomic
def _cancelar_sessoes_seguintes(sessao_original):
    for sessao in _get_sessoes_ativas_a_partir_da_atual(sessao_original):
        if sessao.status == Sessao.Status.PENDENTE:
            sessao.status = Sessao.Status.CANCELADA
            sessao.save(update_fields=["status"])


def _validar_conflitos_edicao_seguintes(sessao_original, form):
    sessoes_da_serie = list(_get_sessoes_ativas_a_partir_da_atual(sessao_original))
    ids_serie = [sessao.id for sessao in sessoes_da_serie]
    posicao_referencia = sessao_original.posicao_na_serie or 1

    for sessao in sessoes_da_serie:
        posicao_atual = sessao.posicao_na_serie or posicao_referencia
        deslocamento_semanas = posicao_atual - posicao_referencia
        nova_data = form.cleaned_data["data"] + datetime.timedelta(days=7 * deslocamento_semanas)

        if not form._validar_conflito_no_horario(
            nova_data,
            form.cleaned_data["horario_inicio"],
            form.cleaned_data["duracao_minutos"],
            excluir_ids=ids_serie,
        ):
            return (
                "Já existe um agendamento nesse horário para "
                f"{nova_data.strftime('%d/%m/%Y')} ao aplicar a alteração nas próximas sessões."
            )

    return None


@transaction.atomic
def _atualizar_sessoes_seguintes(sessao_original, form):
    serie = sessao_original.serie
    sessoes_da_serie = list(_get_sessoes_ativas_a_partir_da_atual(sessao_original))
    posicao_referencia = sessao_original.posicao_na_serie or 1

    if serie.paciente_id != form.cleaned_data["paciente"].id:
        serie.paciente = form.cleaned_data["paciente"]
        serie.save(update_fields=["paciente"])

    for sessao in sessoes_da_serie:
        posicao_atual = sessao.posicao_na_serie or posicao_referencia
        deslocamento_semanas = posicao_atual - posicao_referencia
        sessao.paciente = form.cleaned_data["paciente"]
        sessao.data = form.cleaned_data["data"] + datetime.timedelta(days=7 * deslocamento_semanas)
        sessao.horario_inicio = form.cleaned_data["horario_inicio"]
        sessao.duracao_minutos = form.cleaned_data["duracao_minutos"]
        sessao.valor = form.cleaned_data["valor"]
        sessao.atendido_por_plano = form.cleaned_data["atendido_por_plano"]
        sessao.isento_pagamento = form.cleaned_data["isento_pagamento"]
        sessao.save()


@login_required
def cancelar_sessao_view(request, sessao_id):
    psicologo_perfil = getattr(request.user, "psicologo", None)
    if not psicologo_perfil:
        return redirect("dashboard")

    sessao = get_object_or_404(Sessao, id=sessao_id, psicologo=psicologo_perfil)

    aplicar_em = request.POST.get("cancelar_em", "sessao")
    if aplicar_em == "seguintes" and sessao.serie_id:
        _cancelar_sessoes_seguintes(sessao)
    elif sessao.status == Sessao.Status.PENDENTE:
        sessao.status = Sessao.Status.CANCELADA
        sessao.save()

    return redirect(_get_redirect_destino(request))


def _render_agendamentos(request, psicologo_perfil, form):
    lista_sessoes = _build_sessoes_queryset(psicologo_perfil).order_by(
        "data",
        "horario_inicio",
    )
    data_filtro = _get_data_filtro(request)
    data_referencia = timezone.localdate()

    if data_filtro:
        data_selecionada = parse_date(data_filtro)
        if data_selecionada:
            data_referencia = data_selecionada
            lista_sessoes = lista_sessoes.filter(data=data_selecionada)

    agendamentos_do_dia = _build_sessoes_queryset(psicologo_perfil).filter(
        data=data_referencia,
    ).order_by("horario_inicio")

    inicio_semana = data_referencia
    fim_semana = inicio_semana + datetime.timedelta(days=6)
    agendamentos_da_semana = (
        _build_sessoes_queryset(psicologo_perfil).filter(
            data__range=(inicio_semana, fim_semana),
        )
        .order_by("data", "horario_inicio")
    )

    semana = []
    for deslocamento in range(7):
        dia = inicio_semana + datetime.timedelta(days=deslocamento)
        semana.append(
            {
                "data": dia,
                "agendamentos": [sessao for sessao in agendamentos_da_semana if sessao.data == dia],
            }
        )

    primeiro_dia_mes = data_referencia.replace(day=1)
    ultimo_dia_mes = data_referencia.replace(
        day=calendar.monthrange(data_referencia.year, data_referencia.month)[1]
    )
    agendamentos_do_mes = (
        _build_sessoes_queryset(psicologo_perfil).filter(
            data__range=(primeiro_dia_mes, ultimo_dia_mes),
        )
        .order_by("data", "horario_inicio")
    )
    agendamentos_por_dia = {}
    for sessao in agendamentos_do_mes:
        agendamentos_por_dia.setdefault(sessao.data, []).append(sessao)

    calendario_mes = []
    calendario = calendar.Calendar(firstweekday=6)
    for semana_mes in calendario.monthdatescalendar(
        data_referencia.year,
        data_referencia.month,
    ):
        calendario_mes.append(
            [
                {
                    "data": dia,
                    "fora_do_mes": dia.month != data_referencia.month,
                    "eh_hoje": dia == timezone.localdate(),
                    "eh_referencia": dia == data_referencia,
                    "agendamentos": agendamentos_por_dia.get(dia, []),
                }
                for dia in semana_mes
            ]
        )

    context = {
        "form": form,
        "sessoes": lista_sessoes,
        "data_filtro": data_filtro or "",
        "return_to": request.POST.get("return_to") or request.get_full_path(),
        "aplicar_em": request.POST.get("aplicar_em", "sessao"),
        "data_referencia": data_referencia,
        "agendamentos_do_dia": agendamentos_do_dia,
        "semana": semana,
        "inicio_semana": inicio_semana,
        "fim_semana": fim_semana,
        "calendario_mes": calendario_mes,
        "primeiro_dia_mes": primeiro_dia_mes,
        "ultimo_dia_mes": ultimo_dia_mes,
    }
    return render(request, "agenda/agendamentos_lista.html", context)


@login_required
def agendamentos_view(request):
    psicologo_perfil = getattr(request.user, "psicologo", None)

    if not psicologo_perfil:
        return redirect("dashboard")

    if request.method == "POST":
        form = SessaoForm(request.POST, psicologo=psicologo_perfil)
        if form.is_valid():
            _criar_sessao_ou_serie(psicologo_perfil, form)
            return redirect(_get_redirect_destino(request))
    else:
        form = SessaoForm(psicologo=psicologo_perfil)

    return _render_agendamentos(request, psicologo_perfil, form)


@login_required
def editar_sessao_view(request, sessao_id):
    psicologo_perfil = getattr(request.user, "psicologo", None)
    if not psicologo_perfil:
        return redirect("dashboard")

    sessao = get_object_or_404(Sessao, id=sessao_id, psicologo=psicologo_perfil)

    if request.method == "POST":
        form = SessaoForm(request.POST, instance=sessao, psicologo=psicologo_perfil)
        if form.is_valid():
            aplicar_em = request.POST.get("aplicar_em", "sessao")
            if aplicar_em == "seguintes" and sessao.serie_id:
                mensagem_erro = _validar_conflitos_edicao_seguintes(sessao, form)
                if mensagem_erro:
                    form.add_error(None, mensagem_erro)
                    return _render_agendamentos(request, psicologo_perfil, form)
                _atualizar_sessoes_seguintes(sessao, form)
            else:
                form.save()
            return redirect(_get_redirect_destino(request))

        return _render_agendamentos(request, psicologo_perfil, form)

    return redirect("agenda_lista")

@login_required
@require_POST
def atualizar_status_sessao(request, sessao_id):
    """
    Módulo Interativo (Aba Atendimentos):
    Altera o status da consulta via AJAX/Fetch API sem recarregar a página.
    """
    try:
        
        psicologo = request.user.psicologo
    except AttributeError:
        return JsonResponse({'success': False, 'error': 'Usuário não possui perfil de psicólogo.'}, status=403)
        
    
    sessao = get_object_or_404(Sessao, id=sessao_id, psicologo=psicologo)
    
    try:
        data = json.loads(request.body)
        novo_status = data.get('status')
        
        
        if novo_status not in Sessao.Status.values:
            return JsonResponse({'success': False, 'error': 'Status inválido.'}, status=400)
        
        if sessao.status != novo_status:
            sessao.status = novo_status
            
            
            sessao.save()
            
        return JsonResponse({
            'success': True, 
            'pode_evoluir': sessao.pode_evoluir,
            'message': 'Status atualizado com sucesso.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)