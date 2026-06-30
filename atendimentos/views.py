import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import Paciente, Sessao, DiarioPensamento

from .models import (
    CompartilhamentoSupervisao,
    LogAcessoCompartilhamentoSupervisao,
    Prontuario,
)
from .services import (
    encrypt_prontuario_payload,
    serialize_prontuario,
    serialize_prontuario_supervisao,
)
from datetime import datetime
from django.utils.timezone import make_aware

@login_required
def atendimentos_view(request):
    sessoes_realizadas = []

    try:
        psicologo = request.user.psicologo
    except AttributeError:
        psicologo = None

    if psicologo:
        sessoes_queryset = (
            Sessao.objects.select_related("paciente")
            .filter(psicologo=psicologo, status=Sessao.Status.REALIZADA)
            .order_by("-data", "-horario_inicio")
        )
        prontuarios_por_sessao = {
            prontuario.sessao_id
            for prontuario in Prontuario.objects.filter(sessao__in=sessoes_queryset).only("sessao_id")
        }
        sessoes_realizadas = [
            {
                "sessao": sessao,
                "tem_prontuario": sessao.id in prontuarios_por_sessao,
            }
            for sessao in sessoes_queryset[:12]
        ]

    return render(
        request,
        "atendimentos/lista.html",
        {
            "sessoes_realizadas": sessoes_realizadas,
        },
    )


@login_required
def atendimento_detalhe_view(request, sessao_id):
    try:
        psicologo = request.user.psicologo
    except AttributeError:
        psicologo = None

    data_inicio_param = request.GET.get("data_inicio", "").strip()
    data_fim_param = request.GET.get("data_fim", "").strip()
    data_inicio = parse_date(data_inicio_param) if data_inicio_param else None
    data_fim = parse_date(data_fim_param) if data_fim_param else None
    erro_filtro_periodo = None

    sessao_selecionada = get_object_or_404(
        Sessao.objects.select_related("paciente", "psicologo"),
        id=sessao_id,
        psicologo=psicologo,
    )
    prontuario_existente = (
        Prontuario.objects.select_related("sessao", "paciente", "psicologo")
        .filter(sessao=sessao_selecionada)
        .first()
    )
    historico_queryset = (
        Prontuario.objects.select_related("sessao", "paciente", "psicologo")
        .filter(paciente=sessao_selecionada.paciente, psicologo=psicologo)
        .order_by("-sessao__data", "-criado_em")
    )

    if data_inicio_param and not data_inicio:
        erro_filtro_periodo = _("Data inicial inválida. Use o formato YYYY-MM-DD.")
    elif data_fim_param and not data_fim:
        erro_filtro_periodo = _("Data final inválida. Use o formato YYYY-MM-DD.")
    elif data_inicio and data_fim and data_inicio > data_fim:
        erro_filtro_periodo = _("A data inicial não pode ser maior que a data final.")
    else:
        if data_inicio:
            historico_queryset = historico_queryset.filter(sessao__data__gte=data_inicio)
        if data_fim:
            historico_queryset = historico_queryset.filter(sessao__data__lte=data_fim)

    historico_prontuarios = [
        serialize_prontuario(prontuario)
        for prontuario in historico_queryset
    ]
    pode_registrar_evolucao = (
        sessao_selecionada.status == Sessao.Status.REALIZADA and prontuario_existente is None
    )
    momento_sessao_atual = datetime.combine(sessao_selecionada.data, sessao_selecionada.horario_inicio)
    if not momento_sessao_atual.tzinfo:
        momento_sessao_atual = make_aware(momento_sessao_atual)

    sessao_anterior = (
        Sessao.objects.filter(
            paciente=sessao_selecionada.paciente,
            status=Sessao.Status.REALIZADA
        )
        .filter(data__lt=sessao_selecionada.data)
        .order_by("-data", "-horario_inicio")
        .first()
    )

    diarios_queryset = DiarioPensamento.objects.filter(paciente=sessao_selecionada.paciente)

    if sessao_anterior:
        momento_sessao_anterior = datetime.combine(sessao_anterior.data, sessao_anterior.horario_inicio)
        if not momento_sessao_anterior.tzinfo:
            momento_sessao_anterior = make_aware(momento_sessao_anterior)
        
        historico_diarios = diarios_queryset.filter(
            criado_em__gt=momento_sessao_anterior,
            criado_em__lte=momento_sessao_atual
        ).order_by("-criado_em")
        
    else:
        historico_diarios = diarios_queryset.filter(
            criado_em__lte=momento_sessao_atual
        ).order_by("-criado_em")

    return render(
        request,
        "atendimentos/detalhe.html",
        {
            "sessao_selecionada": sessao_selecionada,
            "prontuario_existente": (
                serialize_prontuario(prontuario_existente) if prontuario_existente else None
            ),
            "historico_prontuarios": historico_prontuarios,
            "filtro_data_inicio": data_inicio_param,
            "filtro_data_fim": data_fim_param,
            "erro_filtro_periodo": erro_filtro_periodo,
            "pode_registrar_evolucao": pode_registrar_evolucao,
            "historico_diarios": historico_diarios,
        },
    )


@login_required
@require_POST
def criar_prontuario_api(request):
    try:
        psicologo = request.user.psicologo
    except AttributeError:
        return JsonResponse({"success": False, "error": _("Usuário não possui perfil de psicólogo.")}, status=403)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": _("JSON inválido.")}, status=400)

    sessao_id = data.get("sessao_id")
    if not sessao_id:
        return JsonResponse({"success": False, "error": _("sessao_id é obrigatório.")}, status=400)

    sessao = get_object_or_404(Sessao, id=sessao_id)

    if sessao.psicologo_id != psicologo.id:
        return JsonResponse(
            {"success": False, "error": _("Você não tem permissão para registrar evolução nesta sessão.")},
            status=403,
        )

    if sessao.status != Sessao.Status.REALIZADA:
        return JsonResponse(
            {
                "success": False,
                "error": _("Só é permitido registrar evolução para sessões com status Realizada."),
            },
            status=400,
        )

    if Prontuario.objects.filter(sessao=sessao).exists():
        return JsonResponse(
            {"success": False, "error": _("Já existe uma evolução registrada para esta sessão.")},
            status=400,
        )

    texto = (data.get("texto") or "").strip()
    humor_paciente = data.get("humor_paciente")
    riscos_identificados = (data.get("riscos_identificados") or "").strip()
    plano_terapeutico = (data.get("plano_terapeutico") or "").strip()

    if not texto:
        return JsonResponse({"success": False, "error": _("texto é obrigatório.")}, status=400)

    encrypted_payload = encrypt_prontuario_payload(
        {
            "texto": texto,
            "riscos_identificados": riscos_identificados,
            "plano_terapeutico": plano_terapeutico,
        }
    )

    prontuario = Prontuario.objects.create(
        sessao=sessao,
        psicologo=psicologo,
        paciente=sessao.paciente,
        texto=encrypted_payload["texto"],
        humor_paciente=humor_paciente,
        riscos_identificados=encrypted_payload["riscos_identificados"],
        plano_terapeutico=encrypted_payload["plano_terapeutico"],
    )

    return JsonResponse(
        {
            "success": True,
            "prontuario": serialize_prontuario(prontuario),
        },
        status=201,
    )


@login_required
@require_http_methods(["PUT"])
def editar_prontuario_api(request, prontuario_id):
    try:
        psicologo = request.user.psicologo
    except AttributeError:
        return JsonResponse({"success": False, "error": _("Usuário não possui perfil de psicólogo.")}, status=403)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": _("JSON inválido.")}, status=400)

    prontuario = get_object_or_404(
        Prontuario.objects.select_related("sessao", "paciente", "psicologo"),
        id=prontuario_id,
    )

    if prontuario.psicologo_id != psicologo.id:
        return JsonResponse(
            {"success": False, "error": _("Você não tem permissão para editar esta evolução.")},
            status=403,
        )

    texto = (data.get("texto") or "").strip()
    humor_paciente = data.get("humor_paciente")
    riscos_identificados = (data.get("riscos_identificados") or "").strip()
    plano_terapeutico = (data.get("plano_terapeutico") or "").strip()

    if not texto:
        return JsonResponse({"success": False, "error": _("texto é obrigatório.")}, status=400)

    encrypted_payload = encrypt_prontuario_payload(
        {
            "texto": texto,
            "riscos_identificados": riscos_identificados,
            "plano_terapeutico": plano_terapeutico,
        }
    )

    prontuario.texto = encrypted_payload["texto"]
    prontuario.humor_paciente = humor_paciente
    prontuario.riscos_identificados = encrypted_payload["riscos_identificados"]
    prontuario.plano_terapeutico = encrypted_payload["plano_terapeutico"]
    prontuario.save(update_fields=["texto", "humor_paciente", "riscos_identificados", "plano_terapeutico", "atualizado_em"])

    return JsonResponse(
        {
            "success": True,
            "prontuario": serialize_prontuario(prontuario),
        }
    )


@login_required
def listar_prontuarios_paciente_api(request, paciente_id):
    try:
        psicologo = request.user.psicologo
    except AttributeError:
        return JsonResponse({"success": False, "error": _("Usuário não possui perfil de psicólogo.")}, status=403)

    paciente = get_object_or_404(Paciente, id=paciente_id)
    if paciente.psicologo_id != psicologo.id:
        return JsonResponse(
            {"success": False, "error": _("Você não tem permissão para acessar os prontuários deste paciente.")},
            status=403,
        )

    data_inicio_param = request.GET.get("data_inicio")
    data_fim_param = request.GET.get("data_fim")
    data_inicio = parse_date(data_inicio_param) if data_inicio_param else None
    data_fim = parse_date(data_fim_param) if data_fim_param else None

    if data_inicio_param and not data_inicio:
        return JsonResponse({"success": False, "error": _("data_inicio inválida. Use o formato YYYY-MM-DD.")}, status=400)

    if data_fim_param and not data_fim:
        return JsonResponse({"success": False, "error": _("data_fim inválida. Use o formato YYYY-MM-DD.")}, status=400)

    if data_inicio and data_fim and data_inicio > data_fim:
        return JsonResponse({"success": False, "error": _("data_inicio não pode ser maior que data_fim.")}, status=400)

    prontuarios = Prontuario.objects.select_related("sessao", "paciente", "psicologo").filter(
        paciente=paciente,
        psicologo=psicologo,
    )

    if data_inicio:
        prontuarios = prontuarios.filter(sessao__data__gte=data_inicio)
    if data_fim:
        prontuarios = prontuarios.filter(sessao__data__lte=data_fim)

    prontuarios = prontuarios.order_by("-sessao__data", "-criado_em")

    return JsonResponse(
        {
            "success": True,
            "prontuarios": [serialize_prontuario(prontuario) for prontuario in prontuarios],
        }
    )


def _get_duracao_supervisao(valor):
    mapa = {
        CompartilhamentoSupervisao.Duracao.VINTE_QUATRO_HORAS: timedelta(hours=24),
        CompartilhamentoSupervisao.Duracao.SETE_DIAS: timedelta(days=7),
    }
    return mapa.get(valor)


def _get_request_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@login_required
@require_POST
def criar_compartilhamento_supervisao_api(request, prontuario_id):
    try:
        psicologo = request.user.psicologo
    except AttributeError:
        return JsonResponse({"success": False, "error": _("Usuário não possui perfil de psicólogo.")}, status=403)

    prontuario = get_object_or_404(
        Prontuario.objects.select_related("sessao", "paciente", "psicologo"),
        id=prontuario_id,
    )
    if prontuario.psicologo_id != psicologo.id:
        return JsonResponse(
            {"success": False, "error": _("Você não tem permissão para compartilhar este caso.")},
            status=403,
        )

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": _("JSON inválido.")}, status=400)

    duracao = data.get("duracao")
    delta = _get_duracao_supervisao(duracao)
    if not delta:
        return JsonResponse(
            {"success": False, "error": _("Duração inválida. Use 24h ou 7d.")},
            status=400,
        )

    compartilhamento = CompartilhamentoSupervisao.objects.create(
        prontuario=prontuario,
        criado_por=psicologo,
        duracao=duracao,
        expira_em=timezone.now() + delta,
    )

    url_compartilhamento = request.build_absolute_uri(
        reverse("supervisao_compartilhada_publica", kwargs={"token": compartilhamento.token})
    )

    return JsonResponse(
        {
            "success": True,
            "url": url_compartilhamento,
            "expira_em": timezone.localtime(compartilhamento.expira_em).strftime("%d/%m/%Y %H:%M"),
        },
        status=201,
    )


def supervisao_compartilhada_publica_view(request, token):
    compartilhamento = get_object_or_404(
        CompartilhamentoSupervisao.objects.select_related(
            "prontuario__sessao",
            "prontuario__paciente",
            "prontuario__psicologo",
        ),
        token=token,
    )

    resultado = LogAcessoCompartilhamentoSupervisao.Resultado.SUCESSO
    status_code = 200
    template_name = "atendimentos/supervisao_compartilhada_publica.html"

    if compartilhamento.expirado:
        resultado = LogAcessoCompartilhamentoSupervisao.Resultado.EXPIRADO
        status_code = 410
        template_name = "atendimentos/supervisao_compartilhada_expirada.html"
    else:
        compartilhamento.ultimo_acesso_em = timezone.now()
        compartilhamento.save(update_fields=["ultimo_acesso_em"])

    LogAcessoCompartilhamentoSupervisao.objects.create(
        compartilhamento=compartilhamento,
        resultado=resultado,
        ip_acesso=_get_request_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
    )

    context = {
        "compartilhamento": compartilhamento,
        "caso": serialize_prontuario_supervisao(compartilhamento.prontuario),
    }

    if status_code == 410:
        return render(request, template_name, context, status=410)
    return render(request, template_name, context)
