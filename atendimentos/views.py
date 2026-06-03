import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import Sessao

from .models import Prontuario
from .services import encrypt_prontuario_payload, serialize_prontuario


@login_required
def atendimentos_view(request):
    return render(request, "atendimentos/lista.html")


@login_required
@require_POST
def criar_prontuario_api(request):
    try:
        psicologo = request.user.psicologo
    except AttributeError:
        return JsonResponse({"success": False, "error": "Usuário não possui perfil de psicólogo."}, status=403)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "JSON inválido."}, status=400)

    sessao_id = data.get("sessao_id")
    if not sessao_id:
        return JsonResponse({"success": False, "error": "sessao_id é obrigatório."}, status=400)

    sessao = get_object_or_404(Sessao, id=sessao_id)

    if sessao.psicologo_id != psicologo.id:
        return JsonResponse(
            {"success": False, "error": "Você não tem permissão para registrar evolução nesta sessão."},
            status=403,
        )

    if sessao.status != Sessao.Status.REALIZADA:
        return JsonResponse(
            {
                "success": False,
                "error": "Só é permitido registrar evolução para sessões com status Realizada.",
            },
            status=400,
        )

    if Prontuario.objects.filter(sessao=sessao).exists():
        return JsonResponse(
            {"success": False, "error": "Já existe uma evolução registrada para esta sessão."},
            status=400,
        )

    texto = (data.get("texto") or "").strip()
    humor_paciente = data.get("humor_paciente")
    riscos_identificados = (data.get("riscos_identificados") or "").strip()
    plano_terapeutico = (data.get("plano_terapeutico") or "").strip()

    if not texto:
        return JsonResponse({"success": False, "error": "texto é obrigatório."}, status=400)

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
        return JsonResponse({"success": False, "error": "Usuário não possui perfil de psicólogo."}, status=403)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "JSON inválido."}, status=400)

    prontuario = get_object_or_404(
        Prontuario.objects.select_related("sessao", "paciente", "psicologo"),
        id=prontuario_id,
    )

    if prontuario.psicologo_id != psicologo.id:
        return JsonResponse(
            {"success": False, "error": "Você não tem permissão para editar esta evolução."},
            status=403,
        )

    texto = (data.get("texto") or "").strip()
    humor_paciente = data.get("humor_paciente")
    riscos_identificados = (data.get("riscos_identificados") or "").strip()
    plano_terapeutico = (data.get("plano_terapeutico") or "").strip()

    if not texto:
        return JsonResponse({"success": False, "error": "texto é obrigatório."}, status=400)

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
