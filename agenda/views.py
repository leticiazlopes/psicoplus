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
from django.views.decorators.csrf import csrf_exempt

import json
from django.http import JsonResponse
from accounts.models import HistoricoStatusSessao, Sessao
from django.views.decorators.http import require_POST
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
import logging
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings

logger = logging.getLogger(__name__)

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


@login_required
@require_POST
def enviar_confirmacao_email(request, sessao_id):
    try:
        psicologo = request.user.psicologo
    except AttributeError:
        return JsonResponse({'success': False, 'error': 'Usuário não possui perfil de psicólogo.'}, status=403)

    sessao = get_object_or_404(Sessao, id=sessao_id, psicologo=psicologo)
    paciente = sessao.paciente

    if not paciente.email:
        return JsonResponse({'success': False, 'error': 'Paciente não possui e-mail cadastrado.'}, status=400)

    if not paciente.aceita_lembrete_email:
        return JsonResponse({'success': False, 'error': 'Paciente não aceita lembretes por e-mail.'}, status=400)

    token = sessao.token_confirmacao
    confirm_url = request.build_absolute_uri(reverse('visualizar_confirmacao_publica', args=[token]))

    assunto = f"Confirmação de agendamento - {sessao.psicologo.usuario.nome}"
    corpo = (
        f"Olá {paciente.nome_completo},\n\n"
        f"Você possui um agendamento em {sessao.data.strftime('%d/%m/%Y')} às {sessao.horario_inicio.strftime('%H:%M')}.\n"
        f"Para confirmar sua presença, acesse: {confirm_url}\n\n"
        f"Atenciosamente,\n{sessao.psicologo.usuario.nome}"
    )

    # HTML com a mesma identidade visual do e-mail de recuperação de senha
    html_message = f"""
    <div style="background-color: #f7f5ff; padding: 30px; font-family: sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 20px; border: 1px solid #e7e9f2;">
            <h2 style="color: #1e293b; font-size: 24px; margin-top: 0;">Confirmação de Agendamento — Psico+</h2>
            <p style="font-size: 15px; line-height: 1.6; color: #475569;">Olá {paciente.nome_completo},</p>
            <p style="font-size: 15px; line-height: 1.6; color: #475569;">Seu agendamento está marcado para <strong>{sessao.data.strftime('%d/%m/%Y')}</strong> às <strong>{sessao.horario_inicio.strftime('%H:%M')}</strong>.</p>
            <div style="text-align:center; margin: 20px 0;">
                <a href="{confirm_url}" style="display:inline-block; padding:12px 20px; background:linear-gradient(90deg,#06b6d4,#3b82f6); color:#fff; border-radius:10px; text-decoration:none; font-weight:bold;">Confirmar presença</a>
            </div>
            <p style="color: #64748b; font-size: 13px; line-height: 1.6; margin-bottom: 0; border-top: 1px solid #f1f5f9; padding-top: 20px;">Se você não reconhece este agendamento, ignore este e-mail ou entre em contato com sua clínica.</p>
            <p style="color: #64748b; font-size: 13px; line-height: 1.6; margin-top: 12px;">Atenciosamente,<br/>{sessao.psicologo.usuario.nome}</p>
        </div>
    </div>
    """

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or None

    # Em ambiente de desenvolvimento, apenas exibe o conteúdo do e-mail no terminal/log.
    if getattr(settings, 'DEBUG', False):
        logger.info('--- E-mail de confirmação (simulado) ---')
        logger.info('Para: %s', paciente.email)
        logger.info('Assunto: %s', assunto)
        logger.info('Corpo (texto):\n%s', corpo)
        logger.info('Corpo (HTML):\n%s', html_message)
        logger.info('--- FIM E-mail ---')
        # também printa para facilitar visualização direta no terminal
        print('\n--- E-mail de confirmação (simulado) ---')
        print('Para:', paciente.email)
        print('Assunto:', assunto)
        print('\nCorpo (texto):\n', corpo)
        print('\nCorpo (HTML):\n', html_message)
        print('--- FIM E-mail ---\n')
        debug_user = None
        try:
            debug_user = request.user.email if request.user.is_authenticated else None
        except Exception:
            debug_user = None
        return JsonResponse({'success': True, 'html': html_message, 'debug_user': debug_user})

    try:
        send_mail(subject=assunto, message=corpo, from_email=from_email, recipient_list=[paciente.email], html_message=html_message, fail_silently=False)
        return JsonResponse({'success': True, 'message': 'E-mail de confirmação enviado.'})
    except BadHeaderError:
        return JsonResponse({'success': False, 'error': 'Cabeçalho de e-mail inválido.'}, status=500)
    except Exception as e:
        logger.exception('Erro ao enviar e-mail de confirmação')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

class DetalheConfirmacaoPublicaView(View):
    def get(self, request, token):
        sessao = get_object_or_404(Sessao, token_confirmacao=token)
        
        context = {
            'sessao': sessao,
            'token_valido': True,
            'erro_codigo': None,
            'token': token,
        }

        if sessao.link_expirado:
            context['token_valido'] = False
            context['erro_codigo'] = 'EXPIRADO'
            context['mensagem_erro'] = 'Link expirado. A sessão já passou.'
        elif sessao.status == Sessao.Status.CONFIRMADA:
            context['token_valido'] = False
            context['erro_codigo'] = 'JA_CONFIRMADO'
            context['mensagem_erro'] = 'Presença já confirmada.'

        return render(request, "agenda/confirmar_presenca_publica.html", context)

    def post(self, request, token):
        sessao = get_object_or_404(Sessao, token_confirmacao=token)

        
        if sessao.link_expirado:
            messages.error(request, 'Link expirado. A sessão já passou.')
            return redirect('visualizar_confirmacao_publica', token=token)

        if sessao.status == Sessao.Status.CONFIRMADA:
            messages.info(request, 'Presença já confirmada.')
            return redirect('visualizar_confirmacao_publica', token=token)

        
        sessao.status = Sessao.Status.CONFIRMADA
        sessao.confirmado_por = 'paciente'
        sessao.confirmado_en = timezone.now() 
        sessao.save()

        messages.success(request, 'Presença confirmada com sucesso!')
        return redirect('visualizar_confirmacao_publica', token=token)

@csrf_exempt
def api_publica_confirmar(request, token):
    try:
        sessao = Sessao.objects.get(token_confirmacao=token)
    except Sessao.DoesNotExist:
        return JsonResponse({"error": "Link de confirmação inválido."}, status=404)

    # Subtask: Token já usado retorna status 400 com mensagem específica
    if sessao.status == Sessao.Status.CONFIRMADA:
        return JsonResponse({"error": "Presença já confirmada."}, status=400)

    # Subtask: Token expirado retorna status 400 com mensagem específica
    if sessao.link_expirado:
        return JsonResponse({"error": "Link expirado. A sessão já passou."}, status=400)

    # Resposta para o carregamento inicial da página (GET)
    if request.method == "GET":
        return JsonResponse({
            "paciente": sessao.paciente.nome_completo if hasattr(sessao.paciente, 'nome_completo') else str(sessao.paciente),
            "psicologo": sessao.psicologo.usuario.nome if hasattr(sessao.psicologo.usuario, 'nome') else str(sessao.psicologo),
            "data": sessao.data.strftime("%d/%m/%Y"),
            "horario_inicio": sessao.horario_inicio.strftime("%H:%M"),
        })

    # Resposta para a ação do clique do botão (POST)
    elif request.method == "POST":
        sessao.status = Sessao.Status.CONFIRMADA
        sessao.confirmado_por = "paciente"
        sessao.confirmado_em = timezone.now()
        sessao.save()
        return JsonResponse({"success": True, "message": "Presença confirmada com sucesso!"})

    return JsonResponse({"error": "Método não permitido."}, status=405)


@login_required
def api_status_sessoes(request):
    ids_param = request.GET.get('ids', '')
    if not ids_param:
        return JsonResponse({'ids': {} })

    ids = [i for i in ids_param.split(',') if i]
    psicologo = getattr(request.user, 'psicologo', None)
    if not psicologo:
        return JsonResponse({'error': 'Não autorizado.'}, status=403)

    sessoes = Sessao.objects.filter(id__in=ids, psicologo=psicologo).values('id', 'status', 'confirmado_por', 'confirmado_em')
    mapping = {
        str(s['id']): {
            'status': s['status'],
            'confirmado_por': s['confirmado_por'],
            'confirmado_em': s['confirmado_em'].isoformat() if s['confirmado_em'] else None,
        }
        for s in sessoes
    }
    return JsonResponse({'ids': mapping})

@login_required
@require_POST
def confirmar_sessao_psicologo(request, sessao_id):
    psicologo_perfil = getattr(request.user, "psicologo", None)
    if not psicologo_perfil:
        return JsonResponse({'success': False, 'error': 'Não autorizado.'}, status=403)

    sessao = get_object_or_404(Sessao, id=sessao_id, psicologo=psicologo_perfil)

    if sessao.status != Sessao.Status.PENDENTE:
        return JsonResponse({'success': False, 'error': 'Apenas sessões pendentes podem ser confirmadas.'}, status=400)

    sessao.status = Sessao.Status.CONFIRMADA
    sessao.confirmado_por = 'psicologo'
    sessao.confirmado_em = timezone.now()
    sessao.save()

    # Simplificado para garantir que retorne JSON para a requisição do botão da agenda
    return JsonResponse({
        'success': True,
        'status_novo': sessao.status,
        'confirmado_por': sessao.confirmado_por,
        'message': 'Presença confirmada pelo psicólogo com sucesso.'
    })