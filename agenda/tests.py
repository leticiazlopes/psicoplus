import datetime

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from accounts.models import Paciente, Psicologo, SerieSessao, Sessao, Usuario

from .forms import SessaoForm


class SessaoFormTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="psico1@teste.com",
            email="psico1@teste.com",
            password="senha123",
            perfil=Usuario.Perfil.PSICOLOGO,
        )
        self.psicologo = Psicologo.objects.create(usuario=self.user, crp="12345")
        self.paciente = Paciente.objects.create(
            nome_completo="Paciente Um",
            psicologo=self.psicologo,
            email="paciente1@teste.com",
            ativo=True,
        )

        self.data_agendamento = datetime.date.today() + datetime.timedelta(days=1)

        Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data=self.data_agendamento,
            horario_inicio=datetime.time(10, 0),
            duracao_minutos=50,
            valor="150.00",
        )

    def _build_form(self, horario_inicio, duracao_minutos):
        return SessaoForm(
            data={
                "paciente": str(self.paciente.pk),
                "data": self.data_agendamento.isoformat(),
                "horario_inicio": horario_inicio,
                "duracao_minutos": duracao_minutos,
                "valor": "180.00",
            },
            psicologo=self.psicologo,
        )

    def test_agendamento_com_conflito_de_horario_e_invalido(self):
        form = self._build_form("10:30", 50)

        self.assertFalse(form.is_valid())
        self.assertIn(
            "Já existe um agendamento nesse horário. Escolha outro intervalo.",
            form.non_field_errors(),
        )

    def test_agendamento_que_engloba_intervalo_existente_e_invalido(self):
        form = self._build_form("09:30", 90)

        self.assertFalse(form.is_valid())
        self.assertIn(
            "Já existe um agendamento nesse horário. Escolha outro intervalo.",
            form.non_field_errors(),
        )

    def test_agendamento_sem_conflito_de_horario_e_valido(self):
        form = self._build_form("11:00", 50)

        self.assertTrue(form.is_valid())

    def test_agendamento_por_plano_forca_valor_zero(self):
        form = SessaoForm(
            data={
                "paciente": str(self.paciente.pk),
                "data": self.data_agendamento.isoformat(),
                "horario_inicio": "11:00",
                "duracao_minutos": 50,
                "valor": "180.00",
                "atendido_por_plano": "on",
            },
            psicologo=self.psicologo,
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["valor"], 0)

    def test_agendamento_sem_plano_ou_isencao_exige_valor_maior_que_zero(self):
        form = SessaoForm(
            data={
                "paciente": str(self.paciente.pk),
                "data": self.data_agendamento.isoformat(),
                "horario_inicio": "11:00",
                "duracao_minutos": 50,
                "valor": "0.00",
            },
            psicologo=self.psicologo,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("valor", form.errors)

    def test_agendamento_recorrente_exige_quantidade_de_repeticoes(self):
        form = SessaoForm(
            data={
                "paciente": str(self.paciente.pk),
                "data": self.data_agendamento.isoformat(),
                "horario_inicio": "11:00",
                "duracao_minutos": 50,
                "valor": "180.00",
                "eh_recorrente": "on",
            },
            psicologo=self.psicologo,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("repeticoes", form.errors)


class SessaoViewsTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="psico2@teste.com",
            email="psico2@teste.com",
            password="senha123",
            perfil=Usuario.Perfil.PSICOLOGO,
        )
        self.psicologo = Psicologo.objects.create(usuario=self.user, crp="54321")
        self.paciente = Paciente.objects.create(
            nome_completo="Paciente Dois",
            psicologo=self.psicologo,
            email="paciente2@teste.com",
            ativo=True,
        )
        self.sessao = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data=datetime.date.today() + datetime.timedelta(days=2),
            horario_inicio=datetime.time(14, 0),
            duracao_minutos=50,
            valor="120.00",
        )
        self.client.force_login(self.user)

    def test_editar_sessao_redireciona_para_data_filtrada_original(self):
        response = self.client.post(
            reverse("editar_sessao", args=[self.sessao.id]),
            data={
                "paciente": str(self.paciente.pk),
                "data": self.sessao.data.isoformat(),
                "horario_inicio": "15:00",
                "duracao_minutos": 50,
                "valor": "150.00",
                "return_to": f"{reverse('agenda_lista')}?data={self.sessao.data.isoformat()}",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('agenda_lista')}?data={self.sessao.data.isoformat()}",
            fetch_redirect_response=False,
        )

    def test_cancelar_sessao_redireciona_para_data_filtrada_original(self):
        response = self.client.post(
            reverse("cancelar_sessao", args=[self.sessao.id]),
            data={
                "return_to": f"{reverse('agenda_lista')}?data={self.sessao.data.isoformat()}",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('agenda_lista')}?data={self.sessao.data.isoformat()}",
            fetch_redirect_response=False,
        )

    def test_agendar_sessao_recorrente_cria_serie_com_todas_as_ocorrencias(self):
        data_inicial = datetime.date.today() + datetime.timedelta(days=3)

        response = self.client.post(
            reverse("agenda_lista"),
            data={
                "paciente": str(self.paciente.pk),
                "data": data_inicial.isoformat(),
                "horario_inicio": "16:00",
                "duracao_minutos": 50,
                "valor": "200.00",
                "eh_recorrente": "on",
                "repeticoes": 4,
            },
        )

        self.assertRedirects(response, reverse("agenda_lista"), fetch_redirect_response=False)

        sessoes = Sessao.objects.filter(
            psicologo=self.psicologo,
            paciente=self.paciente,
            horario_inicio=datetime.time(16, 0),
        ).order_by("data")

        self.assertEqual(sessoes.count(), 4)
        self.assertTrue(all(sessao.serie_id for sessao in sessoes))
        self.assertEqual(len({sessao.serie_id for sessao in sessoes}), 1)
        self.assertEqual([sessao.posicao_na_serie for sessao in sessoes], [1, 2, 3, 4])
        self.assertEqual(
            [sessao.data for sessao in sessoes],
            [
                data_inicial,
                data_inicial + datetime.timedelta(days=7),
                data_inicial + datetime.timedelta(days=14),
                data_inicial + datetime.timedelta(days=21),
            ],
        )


class SerieSessaoTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="psico3@teste.com",
            email="psico3@teste.com",
            password="senha123",
            perfil=Usuario.Perfil.PSICOLOGO,
        )
        self.psicologo = Psicologo.objects.create(usuario=self.user, crp="67890")
        self.paciente = Paciente.objects.create(
            nome_completo="Paciente Três",
            psicologo=self.psicologo,
            email="paciente3@teste.com",
            ativo=True,
        )

    def test_sessoes_podem_ser_agrupadas_em_uma_mesma_serie(self):
        serie = SerieSessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
        )

        primeira_sessao = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            serie=serie,
            posicao_na_serie=1,
            data=datetime.date.today() + datetime.timedelta(days=7),
            horario_inicio=datetime.time(9, 0),
            duracao_minutos=50,
            valor="120.00",
        )
        segunda_sessao = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            serie=serie,
            posicao_na_serie=2,
            data=datetime.date.today() + datetime.timedelta(days=14),
            horario_inicio=datetime.time(9, 0),
            duracao_minutos=50,
            valor="120.00",
        )

        self.assertEqual(primeira_sessao.serie_id, serie.id)
        self.assertEqual(segunda_sessao.serie_id, serie.id)
        self.assertEqual(serie.sessoes.count(), 2)

    def test_posicao_na_serie_deve_ser_unica_dentro_da_mesma_serie(self):
        serie = SerieSessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
        )

        Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            serie=serie,
            posicao_na_serie=1,
            data=datetime.date.today() + datetime.timedelta(days=7),
            horario_inicio=datetime.time(9, 0),
            duracao_minutos=50,
            valor="120.00",
        )

        with self.assertRaises(IntegrityError):
            Sessao.objects.create(
                psicologo=self.psicologo,
                paciente=self.paciente,
                serie=serie,
                posicao_na_serie=1,
                data=datetime.date.today() + datetime.timedelta(days=14),
                horario_inicio=datetime.time(9, 0),
                duracao_minutos=50,
                valor="120.00",
            )
