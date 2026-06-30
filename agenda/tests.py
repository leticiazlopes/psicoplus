import datetime, decimal
from pathlib import Path

from django.db import IntegrityError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from accounts.models import Paciente, Psicologo, SerieSessao, Sessao, Usuario

from .forms import SessaoForm
from .views import _build_sessoes_queryset


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
            "Já existe um agendamento nesse horário para",
            form.non_field_errors()[0],
        )

    def test_agendamento_que_engloba_intervalo_existente_e_invalido(self):
        form = self._build_form("09:30", 90)

        self.assertFalse(form.is_valid())
        self.assertIn(
            "Já existe um agendamento nesse horário para",
            form.non_field_errors()[0],
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

    def test_agendamento_recorrente_valida_conflito_em_qualquer_ocorrencia_da_serie(self):
        Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data=self.data_agendamento + datetime.timedelta(days=14),
            horario_inicio=datetime.time(11, 0),
            duracao_minutos=50,
            valor="150.00",
        )

        form = SessaoForm(
            data={
                "paciente": str(self.paciente.pk),
                "data": self.data_agendamento.isoformat(),
                "horario_inicio": "11:00",
                "duracao_minutos": 50,
                "valor": "180.00",
                "eh_recorrente": "on",
                "repeticoes": 4,
            },
            psicologo=self.psicologo,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            f"{(self.data_agendamento + datetime.timedelta(days=14)).strftime('%d/%m/%Y')}",
            form.non_field_errors()[0],
        )


class AgendaTemplateTests(SimpleTestCase):
    def test_template_exibe_botao_abrir_atendimento_apenas_para_status_realizada(self):
        template_path = Path(__file__).resolve().parent.parent / "templates" / "agenda" / "agendamentos_lista.html"
        template_content = template_path.read_text(encoding="utf-8")

        self.assertIn('data-registrar-evolucao-botao', template_content)
        self.assertIn('x-show="currentStatus === \'realizada\'"', template_content)
        self.assertIn('Abrir atendimento', template_content)
        self.assertIn("{% url 'atendimento_detalhe' sessao.id %}", template_content)


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

    def test_cancelar_sessao_recorrente_pode_cancelar_somente_a_atual(self):
        serie = SerieSessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
        )
        primeira = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            serie=serie,
            posicao_na_serie=1,
            data=self.sessao.data,
            horario_inicio=datetime.time(15, 0),
            duracao_minutos=50,
            valor="180.00",
        )
        segunda = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            serie=serie,
            posicao_na_serie=2,
            data=self.sessao.data + datetime.timedelta(days=7),
            horario_inicio=datetime.time(15, 0),
            duracao_minutos=50,
            valor="180.00",
        )

        response = self.client.post(
            reverse("cancelar_sessao", args=[primeira.id]),
            data={
                "cancelar_em": "sessao",
                "return_to": f"{reverse('agenda_lista')}?data={primeira.data.isoformat()}",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('agenda_lista')}?data={primeira.data.isoformat()}",
            fetch_redirect_response=False,
        )
        primeira.refresh_from_db()
        segunda.refresh_from_db()
        self.assertEqual(primeira.status, Sessao.Status.CANCELADA)
        self.assertEqual(segunda.status, Sessao.Status.PENDENTE)

    def test_cancelar_sessao_recorrente_pode_cancelar_atual_e_seguintes(self):
        serie = SerieSessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
        )
        anterior = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            serie=serie,
            posicao_na_serie=1,
            data=self.sessao.data - datetime.timedelta(days=7),
            horario_inicio=datetime.time(15, 0),
            duracao_minutos=50,
            valor="180.00",
        )
        atual = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            serie=serie,
            posicao_na_serie=2,
            data=self.sessao.data,
            horario_inicio=datetime.time(15, 0),
            duracao_minutos=50,
            valor="180.00",
        )
        proxima = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            serie=serie,
            posicao_na_serie=3,
            data=self.sessao.data + datetime.timedelta(days=7),
            horario_inicio=datetime.time(15, 0),
            duracao_minutos=50,
            valor="180.00",
        )

        response = self.client.post(
            reverse("cancelar_sessao", args=[atual.id]),
            data={
                "cancelar_em": "seguintes",
                "return_to": f"{reverse('agenda_lista')}?data={atual.data.isoformat()}",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('agenda_lista')}?data={atual.data.isoformat()}",
            fetch_redirect_response=False,
        )
        anterior.refresh_from_db()
        atual.refresh_from_db()
        proxima.refresh_from_db()
        self.assertEqual(anterior.status, Sessao.Status.PENDENTE)
        self.assertEqual(atual.status, Sessao.Status.CANCELADA)
        self.assertEqual(proxima.status, Sessao.Status.CANCELADA)

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

    def test_queryset_da_agenda_traz_metadados_da_serie_para_exibicao_visual(self):
        serie = SerieSessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
        )
        sessao_recorrente = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            serie=serie,
            posicao_na_serie=1,
            data=self.sessao.data,
            horario_inicio=datetime.time(15, 30),
            duracao_minutos=50,
            valor="180.00",
        )
        Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            serie=serie,
            posicao_na_serie=2,
            data=self.sessao.data + datetime.timedelta(days=7),
            horario_inicio=datetime.time(15, 30),
            duracao_minutos=50,
            valor="180.00",
        )

        sessao_anotada = _build_sessoes_queryset(self.psicologo).get(id=sessao_recorrente.id)

        self.assertEqual(sessao_anotada.posicao_na_serie, 1)
        self.assertEqual(sessao_anotada.total_sessoes_serie, 2)


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

class SessaoConfirmacaoPublicaTests(TestCase):
    """Testes para o fluxo de confirmação pública de sessões."""
    
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="psico2@teste.com",
            email="psico2@teste.com",
            password="senha123",
            perfil=Usuario.Perfil.PSICOLOGO,
        )
        self.psicologo = Psicologo.objects.create(usuario=self.user, crp="12345")
        self.paciente = Paciente.objects.create(
            nome_completo="Paciente Confirmação",
            psicologo=self.psicologo,
            email="paciente_confirm@teste.com",
            ativo=True,
        )

    def test_confirmacao_publica_com_token_valido(self):
        """Testa GET na página de confirmação pública com token válido."""
        sessao = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data=datetime.date.today() + datetime.timedelta(days=3),
            horario_inicio=datetime.time(15, 0),
            duracao_minutos=50,
            valor="150.00",
            status=Sessao.Status.PENDENTE,
        )
        token = sessao.token_confirmacao
        url = reverse('visualizar_confirmacao_publica', kwargs={'token': token})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('token_valido', response.context)
        self.assertTrue(response.context['token_valido'])

    def test_confirmacao_publica_sessao_ja_confirmada(self):
        """Testa GET quando sessão já está confirmada."""
        sessao = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data=datetime.date.today() + datetime.timedelta(days=3),
            horario_inicio=datetime.time(15, 0),
            duracao_minutos=50,
            valor="150.00",
            status=Sessao.Status.CONFIRMADA,
            confirmado_por='paciente',
            confirmado_em=datetime.datetime.now(),
        )
        token = sessao.token_confirmacao
        url = reverse('visualizar_confirmacao_publica', kwargs={'token': token})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['token_valido'])
        self.assertEqual(response.context['erro_codigo'], 'JA_CONFIRMADO')

    def test_api_publica_confirmar_get_sessao_valida(self):
        """Testa GET na API pública para retornar dados da sessão."""
        sessao = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data=datetime.date.today() + datetime.timedelta(days=3),
            horario_inicio=datetime.time(15, 0),
            duracao_minutos=50,
            valor="150.00",
            status=Sessao.Status.PENDENTE,
        )
        token = sessao.token_confirmacao
        url = reverse('api_publica_confirmar', kwargs={'token': token})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['paciente'], self.paciente.nome_completo)
        self.assertIn('psicologo', data)
        self.assertIn('data', data)
        self.assertIn('horario_inicio', data)

    def test_api_publica_confirmar_post_sucesso(self):
        """Testa POST na API pública para confirmar presença."""
        sessao = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data=datetime.date.today() + datetime.timedelta(days=3),
            horario_inicio=datetime.time(15, 0),
            duracao_minutos=50,
            valor="150.00",
            status=Sessao.Status.PENDENTE,
        )
        token = sessao.token_confirmacao
        url = reverse('api_publica_confirmar', kwargs={'token': token})
        response = self.client.post(url, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        sessao.refresh_from_db()
        self.assertEqual(sessao.status, Sessao.Status.CONFIRMADA)
        self.assertEqual(sessao.confirmado_por, 'paciente')
        self.assertIsNotNone(sessao.confirmado_em)

    def test_api_publica_confirmar_sessao_ja_confirmada(self):
        """Testa erro quando tentando confirmar sessão já confirmada."""
        sessao = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data=datetime.date.today() + datetime.timedelta(days=3),
            horario_inicio=datetime.time(15, 0),
            duracao_minutos=50,
            valor="150.00",
            status=Sessao.Status.CONFIRMADA,
            confirmado_por='paciente',
            confirmado_em=datetime.datetime.now(),
        )
        token = sessao.token_confirmacao
        url = reverse('api_publica_confirmar', kwargs={'token': token})
        response = self.client.post(url, content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_atualizar_status_sessao_autenticado(self):
        """Testa atualização de status via AJAX com psicólogo autenticado."""
        self.client.force_login(self.user)
        sessao = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data=datetime.date.today() + datetime.timedelta(days=3),
            horario_inicio=datetime.time(15, 0),
            duracao_minutos=50,
            valor="150.00",
            status=Sessao.Status.PENDENTE,
        )
        
        url = reverse('atualizar_status_sessao', kwargs={'sessao_id': sessao.id})
        response = self.client.post(
            url,
            data='{"status": "realizada"}',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        sessao.refresh_from_db()
        self.assertEqual(sessao.status, Sessao.Status.REALIZADA)

    def test_api_status_sessoes_retorna_multiplas_sessoes(self):
        """Testa API de polling que retorna status de múltiplas sessões."""
        self.client.force_login(self.user)
        
        sessao1 = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data=datetime.date.today() + datetime.timedelta(days=1),
            horario_inicio=datetime.time(10, 0),
            duracao_minutos=50,
            valor="150.00",
            status=Sessao.Status.CONFIRMADA,
            confirmado_por='paciente',
            confirmado_em=datetime.datetime.now(),
        )
        sessao2 = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data=datetime.date.today() + datetime.timedelta(days=2),
            horario_inicio=datetime.time(15, 0),
            duracao_minutos=50,
            valor="150.00",
            status=Sessao.Status.PENDENTE,
        )
        
        url = reverse('api_status_sessoes')
        response = self.client.get(f'{url}?ids={sessao1.id},{sessao2.id}')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn(str(sessao1.id), data['ids'])
        self.assertIn(str(sessao2.id), data['ids'])
        self.assertEqual(data['ids'][str(sessao1.id)]['status'], Sessao.Status.CONFIRMADA)
        self.assertEqual(data['ids'][str(sessao2.id)]['status'], Sessao.Status.PENDENTE)
        self.assertEqual(data['ids'][str(sessao1.id)]['confirmado_por'], 'paciente')
# Adicionar no final do agenda/tests.py

class AgendaViewsAdicionaisTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="psico4@teste.com",
            email="psico4@teste.com",
            password="senha123",
            perfil=Usuario.Perfil.PSICOLOGO,
        )
        self.psicologo = Psicologo.objects.create(usuario=self.user, crp="11111")
        self.paciente = Paciente.objects.create(
            nome_completo="Paciente Quatro",
            psicologo=self.psicologo,
            email="paciente4@teste.com",
            ativo=True,
        )
        self.sessao = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data=datetime.date.today() + datetime.timedelta(days=2),
            horario_inicio=datetime.time(10, 0),
            duracao_minutos=50,
            valor="150.00",
            status=Sessao.Status.PENDENTE,
        )
        self.client.force_login(self.user)

    # --- AGENDA SEM PERFIL DE PSICÓLOGO ---

    def test_agendamentos_view_sem_perfil_psicologo_redireciona(self):
        user_sem_perfil = Usuario.objects.create_user(
            username="sem@perfil.com",
            email="sem@perfil.com",
            password="123",
            perfil=Usuario.Perfil.PSICOLOGO,
        )
        self.client.force_login(user_sem_perfil)
        response = self.client.get(reverse("agenda_lista"))
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)

    def test_cancelar_sessao_sem_perfil_psicologo_redireciona(self):
        user_sem_perfil = Usuario.objects.create_user(
            username="sem2@perfil.com",
            email="sem2@perfil.com",
            password="123",
            perfil=Usuario.Perfil.PSICOLOGO,
        )
        self.client.force_login(user_sem_perfil)
        response = self.client.post(
            reverse("cancelar_sessao", args=[self.sessao.id]),
            data={"cancelar_em": "sessao"},
        )
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)

    # --- EDITAR SESSÃO ---

    def test_editar_sessao_get_redireciona_para_agenda(self):
        response = self.client.get(
            reverse("editar_sessao", args=[self.sessao.id])
        )
        self.assertRedirects(response, reverse("agenda_lista"), fetch_redirect_response=False)

    def test_editar_sessao_post_valido_salva_alteracoes(self):
        novo_horario = "11:00"
        response = self.client.post(
            reverse("editar_sessao", args=[self.sessao.id]),
            data={
                "paciente": str(self.paciente.pk),
                "data": self.sessao.data.isoformat(),
                "horario_inicio": novo_horario,
                "duracao_minutos": 50,
                "valor": "150.00",
                "aplicar_em": "sessao",
            },
        )
        self.sessao.refresh_from_db()
        self.assertEqual(str(self.sessao.horario_inicio)[:5], novo_horario)

    def test_editar_sessao_post_invalido_retorna_200(self):
        response = self.client.post(
            reverse("editar_sessao", args=[self.sessao.id]),
            data={"paciente": "", "data": "", "horario_inicio": ""},
        )
        self.assertEqual(response.status_code, 200)

    def test_editar_sessao_sem_perfil_psicologo_redireciona(self):
        user_sem_perfil = Usuario.objects.create_user(
            username="sem3@perfil.com",
            email="sem3@perfil.com",
            password="123",
            perfil=Usuario.Perfil.PSICOLOGO,
        )
        self.client.force_login(user_sem_perfil)
        response = self.client.post(
            reverse("editar_sessao", args=[self.sessao.id]),
            data={},
        )
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)

    # --- CONFIRMAR PELO PSICÓLOGO ---

    def test_confirmar_sessao_psicologo_sucesso(self):
        response = self.client.post(
            reverse("confirmar_sessao_psicologo", kwargs={'sessao_id': self.sessao.id})
        )
        ...

    def test_confirmar_sessao_psicologo_ja_confirmada_retorna_erro(self):
        self.sessao.status = Sessao.Status.CONFIRMADA
        self.sessao.save()
        response = self.client.post(
            reverse("confirmar_sessao_psicologo", kwargs={'sessao_id': self.sessao.id})
        )
        ...

    def test_confirmar_sessao_psicologo_sem_perfil_retorna_403(self):
        user_sem_perfil = Usuario.objects.create_user(
            username="sem4@perfil.com",
            email="sem4@perfil.com",
            password="123",
            perfil=Usuario.Perfil.PSICOLOGO,
        )
        self.client.force_login(user_sem_perfil)
        response = self.client.post(
            reverse("confirmar_sessao_psicologo", kwargs={'sessao_id': self.sessao.id})
        )
        ...

    # --- ATUALIZAR STATUS ---

    def test_atualizar_status_status_invalido_retorna_400(self):
        response = self.client.post(
            reverse("atualizar_status_sessao", args=[self.sessao.id]),
            data='{"status": "status_invalido"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_atualizar_status_sem_perfil_retorna_403(self):
        user_sem_perfil = Usuario.objects.create_user(
            username="sem5@perfil.com",
            email="sem5@perfil.com",
            password="123",
            perfil=Usuario.Perfil.PSICOLOGO,
        )
        self.client.force_login(user_sem_perfil)
        response = self.client.post(
            reverse("atualizar_status_sessao", args=[self.sessao.id]),
            data='{"status": "realizada"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    # --- API STATUS SEM IDS ---

    def test_api_status_sessoes_sem_ids_retorna_vazio(self):
        response = self.client.get(reverse("api_status_sessoes"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["ids"], {})

    # --- CONFIRMAÇÃO PÚBLICA EXPIRADA ---

    def test_confirmacao_publica_link_expirado(self):
        sessao_passada = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data=datetime.date.today() - datetime.timedelta(days=1),
            horario_inicio=datetime.time(10, 0),
            duracao_minutos=50,
            valor="150.00",
            status=Sessao.Status.PENDENTE,
        )
        token = sessao_passada.token_confirmacao
        url = reverse("visualizar_confirmacao_publica", kwargs={"token": token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["token_valido"])
        self.assertEqual(response.context["erro_codigo"], "EXPIRADO")

    def test_api_publica_confirmar_link_expirado_retorna_400(self):
        sessao_passada = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data=datetime.date.today() - datetime.timedelta(days=1),
            horario_inicio=datetime.time(10, 0),
            duracao_minutos=50,
            valor="150.00",
            status=Sessao.Status.PENDENTE,
        )
        token = sessao_passada.token_confirmacao
        url = reverse("api_publica_confirmar", kwargs={"token": token})
        response = self.client.post(url, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)

    def test_enviar_confirmacao_email_paciente_sem_email_retorna_400(self):
        paciente_sem_email = Paciente.objects.create(
            nome_completo="Sem Email",
            psicologo=self.psicologo,
            ativo=True,
        )
        sessao = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=paciente_sem_email,
            data=datetime.date.today() + datetime.timedelta(days=1),
            horario_inicio=datetime.time(10, 0),
            duracao_minutos=50,
            valor="150.00",
        )
        response = self.client.post(
            reverse("enviar_confirmacao_email", args=[sessao.id])
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        
class MarcarPagamentoSessaoTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="psico_pagamento@teste.com",
            email="psico_pagamento@teste.com",
            password="senha123",
            perfil=Usuario.Perfil.PSICOLOGO,
        )
        self.psicologo = Psicologo.objects.create(usuario=self.user, crp="99999")
        self.paciente = Paciente.objects.create(
            nome_completo="Paciente Pagamento",
            psicologo=self.psicologo,
            email="paciente_pagamento@teste.com",
            ativo=True,
        )
        self.sessao = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data=datetime.date.today() + datetime.timedelta(days=1),
            horario_inicio=datetime.time(10, 0),
            duracao_minutos=50,
            valor="100.00",
        )
        self.client.force_login(self.user)

    def test_sessao_nasce_com_status_pagamento_pendente_por_default(self):
        self.assertEqual(self.sessao.status_pagamento, Sessao.StatusPagamento.PENDENTE)
        self.assertIsNone(self.sessao.data_pagamento)

    def test_marcar_como_pago_com_data_e_forma_informadas(self):
        url = reverse("marcar_pagamento_sessao", args=[self.sessao.id])
        response = self.client.post(
            url,
            data='{"status_pagamento": "pago", "data_pagamento": "2026-06-15", "forma_pagamento": "pix"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status_pagamento"], "pago")

        self.sessao.refresh_from_db()
        self.assertEqual(self.sessao.status_pagamento, Sessao.StatusPagamento.PAGO)
        self.assertEqual(self.sessao.data_pagamento, datetime.date(2026, 6, 15))
        self.assertEqual(self.sessao.forma_pagamento, "pix")

    def test_marcar_como_pago_sem_data_usa_hoje_como_default(self):
        url = reverse("marcar_pagamento_sessao", args=[self.sessao.id])
        response = self.client.post(
            url,
            data='{"status_pagamento": "pago"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.sessao.refresh_from_db()
        self.assertEqual(self.sessao.data_pagamento, datetime.date.today())

    def test_marcar_como_pendente_limpa_data_pagamento(self):
        self.sessao.status_pagamento = Sessao.StatusPagamento.PAGO
        self.sessao.data_pagamento = datetime.date.today()
        self.sessao.forma_pagamento = "dinheiro"
        self.sessao.save()

        url = reverse("marcar_pagamento_sessao", args=[self.sessao.id])
        response = self.client.post(
            url,
            data='{"status_pagamento": "pendente"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.sessao.refresh_from_db()
        self.assertEqual(self.sessao.status_pagamento, Sessao.StatusPagamento.PENDENTE)
        self.assertIsNone(self.sessao.data_pagamento)

    def test_status_pagamento_invalido_retorna_400(self):
        url = reverse("marcar_pagamento_sessao", args=[self.sessao.id])
        response = self.client.post(
            url,
            data='{"status_pagamento": "quitado"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)

    def test_sem_perfil_psicologo_retorna_403(self):
        user_sem_perfil = Usuario.objects.create_user(
            username="sem_pagamento@teste.com",
            email="sem_pagamento@teste.com",
            password="123",
            perfil=Usuario.Perfil.PSICOLOGO,
        )
        self.client.force_login(user_sem_perfil)

        url = reverse("marcar_pagamento_sessao", args=[self.sessao.id])
        response = self.client.post(
            url,
            data='{"status_pagamento": "pago"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

    def test_sessao_de_outro_psicologo_retorna_404(self):
        outro_user = Usuario.objects.create_user(
            username="outro_psico@teste.com",
            email="outro_psico@teste.com",
            password="123",
            perfil=Usuario.Perfil.PSICOLOGO,
        )
        outro_psicologo = Psicologo.objects.create(usuario=outro_user, crp="88888")
        self.client.force_login(outro_user)

        url = reverse("marcar_pagamento_sessao", args=[self.sessao.id])
        response = self.client.post(
            url,
            data='{"status_pagamento": "pago"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        
class EditarSessaoRecorrenteSeguintesTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="psico_serie@teste.com",
            email="psico_serie@teste.com",
            password="senha123",
            perfil=Usuario.Perfil.PSICOLOGO,
        )
        self.psicologo = Psicologo.objects.create(usuario=self.user, crp="22222")
        self.paciente = Paciente.objects.create(
            nome_completo="Paciente Série Edição",
            psicologo=self.psicologo,
            email="paciente_serie@teste.com",
            ativo=True,
        )
        self.client.force_login(self.user)

        self.serie = SerieSessao.objects.create(psicologo=self.psicologo, paciente=self.paciente)
        self.data_base = datetime.date.today() + datetime.timedelta(days=7)

        self.atual = Sessao.objects.create(
            psicologo=self.psicologo, paciente=self.paciente, serie=self.serie,
            posicao_na_serie=1, data=self.data_base,
            horario_inicio=datetime.time(10, 0), duracao_minutos=50, valor="150.00",
        )
        self.proxima = Sessao.objects.create(
            psicologo=self.psicologo, paciente=self.paciente, serie=self.serie,
            posicao_na_serie=2, data=self.data_base + datetime.timedelta(days=7),
            horario_inicio=datetime.time(10, 0), duracao_minutos=50, valor="150.00",
        )

    def test_editar_aplicando_em_seguintes_atualiza_todas_as_ocorrencias(self):
        response = self.client.post(
            reverse("editar_sessao", args=[self.atual.id]),
            data={
                "paciente": str(self.paciente.pk),
                "data": self.data_base.isoformat(),
                "horario_inicio": "11:00",
                "duracao_minutos": 60,
                "valor": "200.00",
                "aplicar_em": "seguintes",
            },
        )

        self.atual.refresh_from_db()
        self.proxima.refresh_from_db()
        self.assertEqual(str(self.atual.horario_inicio)[:5], "11:00")
        self.assertEqual(str(self.proxima.horario_inicio)[:5], "11:00")
        self.assertEqual(self.atual.valor, decimal.Decimal("200.00"))
        self.assertEqual(self.proxima.valor, decimal.Decimal("200.00"))

    def test_editar_aplicando_em_seguintes_com_conflito_retorna_erro(self):
        Sessao.objects.create(
            psicologo=self.psicologo, paciente=self.paciente,
            data=self.data_base + datetime.timedelta(days=7),
            horario_inicio=datetime.time(11, 30), duracao_minutos=50, valor="150.00",
        )

        response = self.client.post(
            reverse("editar_sessao", args=[self.atual.id]),
            data={
                "paciente": str(self.paciente.pk),
                "data": self.data_base.isoformat(),
                "horario_inicio": "11:00",
                "duracao_minutos": 60,
                "valor": "200.00",
                "aplicar_em": "seguintes",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.atual.refresh_from_db()
        self.assertEqual(str(self.atual.horario_inicio)[:5], "10:00")


class EnvioEmailConfirmacaoSucessoTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="psico_email@teste.com",
            email="psico_email@teste.com",
            password="senha123",
            perfil=Usuario.Perfil.PSICOLOGO,
        )
        self.psicologo = Psicologo.objects.create(usuario=self.user, crp="33333")
        self.paciente = Paciente.objects.create(
            nome_completo="Paciente Email",
            psicologo=self.psicologo,
            email="paciente_email@teste.com",
            ativo=True,
            aceita_lembrete_email=True,
        )
        self.sessao = Sessao.objects.create(
            psicologo=self.psicologo, paciente=self.paciente,
            data=datetime.date.today() + datetime.timedelta(days=1),
            horario_inicio=datetime.time(10, 0), duracao_minutos=50, valor="150.00",
        )
        self.client.force_login(self.user)
        
    @override_settings(DEBUG=True)
    def test_enviar_confirmacao_email_sucesso_modo_debug(self):
        response = self.client.post(
            reverse("enviar_confirmacao_email", args=[self.sessao.id])
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("html", data)

    def test_enviar_confirmacao_email_paciente_nao_aceita_lembrete_retorna_400(self):
        self.paciente.aceita_lembrete_email = False
        self.paciente.save()

        response = self.client.post(
            reverse("enviar_confirmacao_email", args=[self.sessao.id])
        )
        self.assertEqual(response.status_code, 400)

class DetalheConfirmacaoPublicaPostTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="psico_post_pub@teste.com",
            email="psico_post_pub@teste.com",
            password="senha123",
            perfil=Usuario.Perfil.PSICOLOGO,
        )
        self.psicologo = Psicologo.objects.create(usuario=self.user, crp="44444")
        self.paciente = Paciente.objects.create(
            nome_completo="Paciente Confirmação Post",
            psicologo=self.psicologo,
            email="paciente_post_pub@teste.com",
            ativo=True,
        )

    def test_post_confirmacao_publica_sucesso(self):
        sessao = Sessao.objects.create(
            psicologo=self.psicologo, paciente=self.paciente,
            data=datetime.date.today() + datetime.timedelta(days=2),
            horario_inicio=datetime.time(14, 0), duracao_minutos=50, valor="150.00",
            status=Sessao.Status.PENDENTE,
        )
        url = reverse("visualizar_confirmacao_publica", kwargs={"token": sessao.token_confirmacao})
        response = self.client.post(url)

        self.assertRedirects(response, url, fetch_redirect_response=False)
        sessao.refresh_from_db()
        self.assertEqual(sessao.status, Sessao.Status.CONFIRMADA)
        self.assertEqual(sessao.confirmado_por, "paciente")

    def test_post_confirmacao_publica_link_expirado_nao_confirma(self):
        sessao = Sessao.objects.create(
            psicologo=self.psicologo, paciente=self.paciente,
            data=datetime.date.today() - datetime.timedelta(days=1),
            horario_inicio=datetime.time(10, 0), duracao_minutos=50, valor="150.00",
            status=Sessao.Status.PENDENTE,
        )
        url = reverse("visualizar_confirmacao_publica", kwargs={"token": sessao.token_confirmacao})
        response = self.client.post(url)

        self.assertRedirects(response, url, fetch_redirect_response=False)
        sessao.refresh_from_db()
        self.assertEqual(sessao.status, Sessao.Status.PENDENTE)

    def test_post_confirmacao_publica_ja_confirmada_nao_altera(self):
        sessao = Sessao.objects.create(
            psicologo=self.psicologo, paciente=self.paciente,
            data=datetime.date.today() + datetime.timedelta(days=2),
            horario_inicio=datetime.time(10, 0), duracao_minutos=50, valor="150.00",
            status=Sessao.Status.CONFIRMADA,
            confirmado_por="paciente",
            confirmado_em=datetime.datetime.now(),
        )
        url = reverse("visualizar_confirmacao_publica", kwargs={"token": sessao.token_confirmacao})
        response = self.client.post(url)

        self.assertRedirects(response, url, fetch_redirect_response=False)