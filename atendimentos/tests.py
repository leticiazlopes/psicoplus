import json
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import Paciente, Psicologo, Sessao, Usuario

from .models import Prontuario


class CriarProntuarioApiTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="psico@teste.com",
            email="psico@teste.com",
            password="senha123",
            nome="Psicólogo Teste",
            perfil=Usuario.Perfil.PSICOLOGO,
        )
        self.psicologo = Psicologo.objects.create(usuario=self.user, crp="12345")
        self.paciente = Paciente.objects.create(
            nome_completo="Paciente Teste",
            email="paciente@teste.com",
            psicologo=self.psicologo,
        )
        self.sessao_realizada = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data="2026-06-02",
            horario_inicio="10:00",
            duracao_minutos=50,
            valor=Decimal("150.00"),
            status=Sessao.Status.REALIZADA,
        )
        self.sessao_pendente = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data="2026-06-03",
            horario_inicio="10:00",
            duracao_minutos=50,
            valor=Decimal("150.00"),
            status=Sessao.Status.PENDENTE,
        )

    def test_cria_prontuario_para_sessao_realizada(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("criar_prontuario_api"),
            data=json.dumps(
                {
                    "sessao_id": str(self.sessao_realizada.id),
                    "texto": "Paciente relata ansiedade antes das consultas.",
                    "humor_paciente": 7,
                    "riscos_identificados": "Sem risco imediato identificado.",
                    "plano_terapeutico": "Manter acompanhamento semanal.",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["prontuario"]["sessao_id"], str(self.sessao_realizada.id))
        self.assertEqual(payload["prontuario"]["status_sessao"], Sessao.Status.REALIZADA)
        self.assertEqual(payload["prontuario"]["humor_paciente"], 7)
        self.assertTrue(
            Prontuario.objects.filter(
                sessao=self.sessao_realizada,
                texto="Paciente relata ansiedade antes das consultas.",
            ).exists()
        )

    def test_bloqueia_criacao_quando_sessao_nao_esta_realizada(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("criar_prontuario_api"),
            data=json.dumps(
                {
                    "sessao_id": str(self.sessao_pendente.id),
                    "texto": "Tentativa antecipada de evolução.",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "Só é permitido registrar evolução para sessões com status Realizada.",
        )
        self.assertFalse(Prontuario.objects.filter(sessao=self.sessao_pendente).exists())

    def test_bloqueia_segunda_evolucao_para_mesma_sessao(self):
        Prontuario.objects.create(
            sessao=self.sessao_realizada,
            psicologo=self.psicologo,
            paciente=self.paciente,
            texto="Primeira evolução",
            riscos_identificados="Observações iniciais",
            plano_terapeutico="Plano inicial",
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("criar_prontuario_api"),
            data=json.dumps(
                {
                    "sessao_id": str(self.sessao_realizada.id),
                    "texto": "Segunda tentativa",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "Já existe uma evolução registrada para esta sessão.",
        )
