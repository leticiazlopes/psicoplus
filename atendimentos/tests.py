import json
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import Paciente, Psicologo, Sessao, Usuario

from .models import Prontuario
from .services import decrypt_value, encrypt_value, serialize_prontuario


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
        self.outro_user = Usuario.objects.create_user(
            username="outro_psico@teste.com",
            email="outro_psico@teste.com",
            password="senha123",
            nome="Outro Psicólogo",
            perfil=Usuario.Perfil.PSICOLOGO,
        )
        self.outro_psicologo = Psicologo.objects.create(usuario=self.outro_user, crp="54321")

    def test_cria_prontuario_para_sessao_realizada(self):
        self.client.force_login(self.user)
        texto_original = "Paciente relata ansiedade antes das consultas."
        riscos_originais = "Sem risco imediato identificado."
        plano_original = "Manter acompanhamento semanal."

        response = self.client.post(
            reverse("criar_prontuario_api"),
            data=json.dumps(
                {
                    "sessao_id": str(self.sessao_realizada.id),
                    "texto": texto_original,
                    "humor_paciente": 7,
                    "riscos_identificados": riscos_originais,
                    "plano_terapeutico": plano_original,
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
        self.assertEqual(payload["prontuario"]["texto"], texto_original)
        self.assertEqual(payload["prontuario"]["riscos_identificados"], riscos_originais)
        self.assertEqual(payload["prontuario"]["plano_terapeutico"], plano_original)

        prontuario = Prontuario.objects.get(sessao=self.sessao_realizada)
        self.assertNotEqual(prontuario.texto, texto_original)
        self.assertNotEqual(prontuario.riscos_identificados, riscos_originais)
        self.assertNotEqual(prontuario.plano_terapeutico, plano_original)
        self.assertEqual(decrypt_value(prontuario.texto), texto_original)
        self.assertEqual(decrypt_value(prontuario.riscos_identificados), riscos_originais)
        self.assertEqual(decrypt_value(prontuario.plano_terapeutico), plano_original)

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

    def test_retorna_403_quando_sessao_pertence_a_outro_psicologo(self):
        self.client.force_login(self.outro_user)

        response = self.client.post(
            reverse("criar_prontuario_api"),
            data=json.dumps(
                {
                    "sessao_id": str(self.sessao_realizada.id),
                    "texto": "Tentativa sem permissão.",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["error"],
            "Você não tem permissão para registrar evolução nesta sessão.",
        )
        self.assertFalse(Prontuario.objects.filter(texto="Tentativa sem permissão.").exists())

    def test_delete_no_endpoint_de_prontuario_nao_esta_exposto(self):
        self.client.force_login(self.user)

        response = self.client.delete(reverse("criar_prontuario_api"))

        self.assertEqual(response.status_code, 405)

    def test_serialize_prontuario_descriptografa_campos_da_resposta(self):
        prontuario = Prontuario.objects.create(
            sessao=self.sessao_realizada,
            psicologo=self.psicologo,
            paciente=self.paciente,
            texto=encrypt_value("Texto protegido"),
            riscos_identificados=encrypt_value("Risco protegido"),
            plano_terapeutico=encrypt_value("Plano protegido"),
        )
        prontuario.refresh_from_db()

        serialized = serialize_prontuario(prontuario)

        self.assertEqual(serialized["texto"], "Texto protegido")
        self.assertEqual(serialized["riscos_identificados"], "Risco protegido")
        self.assertEqual(serialized["plano_terapeutico"], "Plano protegido")

    def test_decrypt_value_mantem_texto_legado_sem_quebrar(self):
        self.assertEqual(decrypt_value("Texto legado"), "Texto legado")

    def test_edita_prontuario_existente_com_put(self):
        prontuario = Prontuario.objects.create(
            sessao=self.sessao_realizada,
            psicologo=self.psicologo,
            paciente=self.paciente,
            texto=encrypt_value("Texto original"),
            humor_paciente=5,
            riscos_identificados=encrypt_value("Risco original"),
            plano_terapeutico=encrypt_value("Plano original"),
        )
        self.client.force_login(self.user)

        response = self.client.put(
            reverse("editar_prontuario_api", kwargs={"prontuario_id": prontuario.id}),
            data=json.dumps(
                {
                    "texto": "Texto atualizado",
                    "humor_paciente": 9,
                    "riscos_identificados": "Risco atualizado",
                    "plano_terapeutico": "Plano atualizado",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["prontuario"]["texto"], "Texto atualizado")
        self.assertEqual(payload["prontuario"]["humor_paciente"], 9)
        self.assertEqual(payload["prontuario"]["riscos_identificados"], "Risco atualizado")
        self.assertEqual(payload["prontuario"]["plano_terapeutico"], "Plano atualizado")

        prontuario.refresh_from_db()
        self.assertEqual(decrypt_value(prontuario.texto), "Texto atualizado")
        self.assertEqual(decrypt_value(prontuario.riscos_identificados), "Risco atualizado")
        self.assertEqual(decrypt_value(prontuario.plano_terapeutico), "Plano atualizado")

    def test_put_retorna_403_quando_prontuario_pertence_a_outro_psicologo(self):
        prontuario = Prontuario.objects.create(
            sessao=self.sessao_realizada,
            psicologo=self.psicologo,
            paciente=self.paciente,
            texto=encrypt_value("Texto protegido"),
            riscos_identificados=encrypt_value("Risco protegido"),
            plano_terapeutico=encrypt_value("Plano protegido"),
        )
        self.client.force_login(self.outro_user)

        response = self.client.put(
            reverse("editar_prontuario_api", kwargs={"prontuario_id": prontuario.id}),
            data=json.dumps(
                {
                    "texto": "Tentativa sem permissão",
                    "humor_paciente": 2,
                    "riscos_identificados": "Nenhum",
                    "plano_terapeutico": "Nenhum",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["error"],
            "Você não tem permissão para editar esta evolução.",
        )

    def test_lista_prontuarios_do_paciente_ordenados_do_mais_recente_para_o_mais_antigo(self):
        sessao_antiga = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data="2026-05-20",
            horario_inicio="09:00",
            duracao_minutos=50,
            valor=Decimal("150.00"),
            status=Sessao.Status.REALIZADA,
        )
        sessao_recente = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data="2026-06-15",
            horario_inicio="09:00",
            duracao_minutos=50,
            valor=Decimal("150.00"),
            status=Sessao.Status.REALIZADA,
        )
        prontuario_antigo = Prontuario.objects.create(
            sessao=sessao_antiga,
            psicologo=self.psicologo,
            paciente=self.paciente,
            texto=encrypt_value("Texto antigo"),
            riscos_identificados=encrypt_value("Risco antigo"),
            plano_terapeutico=encrypt_value("Plano antigo"),
        )
        prontuario_recente = Prontuario.objects.create(
            sessao=sessao_recente,
            psicologo=self.psicologo,
            paciente=self.paciente,
            texto=encrypt_value("Texto recente"),
            riscos_identificados=encrypt_value("Risco recente"),
            plano_terapeutico=encrypt_value("Plano recente"),
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("listar_prontuarios_paciente_api", kwargs={"paciente_id": self.paciente.id})
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(len(payload["prontuarios"]), 2)
        self.assertEqual(payload["prontuarios"][0]["id"], str(prontuario_recente.id))
        self.assertEqual(payload["prontuarios"][1]["id"], str(prontuario_antigo.id))

    def test_lista_prontuarios_filtra_por_periodo(self):
        sessao_fora_periodo = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data="2026-05-10",
            horario_inicio="09:00",
            duracao_minutos=50,
            valor=Decimal("150.00"),
            status=Sessao.Status.REALIZADA,
        )
        sessao_dentro_periodo = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data="2026-06-10",
            horario_inicio="09:00",
            duracao_minutos=50,
            valor=Decimal("150.00"),
            status=Sessao.Status.REALIZADA,
        )
        Prontuario.objects.create(
            sessao=sessao_fora_periodo,
            psicologo=self.psicologo,
            paciente=self.paciente,
            texto=encrypt_value("Texto fora"),
            riscos_identificados=encrypt_value("Risco fora"),
            plano_terapeutico=encrypt_value("Plano fora"),
        )
        prontuario_dentro = Prontuario.objects.create(
            sessao=sessao_dentro_periodo,
            psicologo=self.psicologo,
            paciente=self.paciente,
            texto=encrypt_value("Texto dentro"),
            riscos_identificados=encrypt_value("Risco dentro"),
            plano_terapeutico=encrypt_value("Plano dentro"),
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("listar_prontuarios_paciente_api", kwargs={"paciente_id": self.paciente.id}),
            {"data_inicio": "2026-06-01", "data_fim": "2026-06-30"},
        )

        self.assertEqual(response.status_code, 200)
        prontuarios = response.json()["prontuarios"]
        self.assertEqual(len(prontuarios), 1)
        self.assertEqual(prontuarios[0]["id"], str(prontuario_dentro.id))

    def test_get_prontuarios_retorna_403_para_outro_psicologo(self):
        self.client.force_login(self.outro_user)

        response = self.client.get(
            reverse("listar_prontuarios_paciente_api", kwargs={"paciente_id": self.paciente.id})
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["error"],
            "Você não tem permissão para acessar os prontuários deste paciente.",
        )

    def test_get_prontuarios_retorna_400_para_periodo_invalido(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("listar_prontuarios_paciente_api", kwargs={"paciente_id": self.paciente.id}),
            {"data_inicio": "2026-06-30", "data_fim": "2026-06-01"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "data_inicio não pode ser maior que data_fim.",
        )
