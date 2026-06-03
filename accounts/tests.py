from pathlib import Path

from django.test import TestCase
from django.urls import resolve, reverse
from datetime import timedelta
from django.utils import timezone
from .forms import CadastroPacienteForm
from .models import Usuario, Psicologo, Paciente, Sessao
from datetime import timedelta
from atendimentos.models import Prontuario
from atendimentos.services import encrypt_value

class PacienteViewTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username='psico1@teste.com', 
            email='psico1@teste.com',
            password='senha123', 
            perfil=Usuario.Perfil.PSICOLOGO
        )
        self.psicologo = Psicologo.objects.create(usuario=self.user, crp="12345")
        
        self.paciente = Paciente.objects.create(
            nome_completo="Paciente Um",
            psicologo=self.psicologo,
            ativo=True
        )

    # --- TESTES DE LISTAGEM E BUSCA ---

    def test_psicologo_so_ve_seus_proprios_pacientes(self):
        outro_user = Usuario.objects.create_user(username='outro@t.com', email='outro@t.com', password='123')
        outro_psico = Psicologo.objects.create(usuario=outro_user, crp="67890")
        Paciente.objects.create(nome_completo="Invasor", psicologo=outro_psico)

        self.client.force_login(self.user)
        response = self.client.get(reverse('pacientes_lista'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['pacientes']), 1)
        self.assertContains(response, "Paciente Um")
        self.assertNotContains(response, "Invasor")

    def test_busca_paciente_por_nome(self):
        self.client.force_login(self.user)
        Paciente.objects.create(nome_completo="Maria Silva", psicologo=self.psicologo)

        response = self.client.get(reverse('pacientes_lista'), {'search': 'Paciente'})
        self.assertEqual(len(response.context['pacientes']), 1)
        self.assertContains(response, "Paciente Um")
        
    def test_psicologo_nao_pode_editar_paciente_de_outro(self):
        # Criamos outro psicólogo e um paciente dele
        outro_user = Usuario.objects.create_user(username='hacker@t.com', email='hacker@t.com', password='123')
        outro_psico = Psicologo.objects.create(usuario=outro_user, crp="999")
        paciente_alheio = Paciente.objects.create(nome_completo="Paciente Privado", psicologo=outro_psico)

        # Logamos com o Psico 1 e tentamos editar o paciente do outro
        self.client.force_login(self.user)
        url = reverse('editar_paciente', kwargs={'pk': paciente_alheio.pk})
        response = self.client.get(url)
        
        # Aqui depende da sua implementação: 
        # Pode retornar 404 (objeto não encontrado no queryset filtrado) ou 403 (Proibido)
        self.assertIn(response.status_code, [404, 403])

    def test_psicologo_pode_ver_perfil_do_proprio_paciente_com_historico(self):
        sessao = Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=self.paciente,
            data="2026-06-03",
            horario_inicio="14:00",
            duracao_minutos=50,
            valor="120.00",
            status=Sessao.Status.REALIZADA,
        )
        prontuario = Prontuario.objects.create(
            sessao=sessao,
            psicologo=self.psicologo,
            paciente=self.paciente,
            texto=encrypt_value("Paciente apresentou melhora"),
            riscos_identificados=encrypt_value("Sem riscos"),
            plano_terapeutico=encrypt_value("Manter acompanhamento"),
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('paciente_perfil', kwargs={'pk': self.paciente.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['paciente'], self.paciente)
        self.assertEqual(response.context['total_evolucoes'], 1)
        self.assertEqual(response.context['historico_prontuarios'][0]['id'], str(prontuario.id))
        self.assertContains(response, "Paciente apresentou melhora")

    def test_psicologo_nao_pode_ver_perfil_de_paciente_de_outro(self):
        outro_user = Usuario.objects.create_user(username='hacker2@t.com', email='hacker2@t.com', password='123')
        outro_psico = Psicologo.objects.create(usuario=outro_user, crp="11111")
        paciente_alheio = Paciente.objects.create(nome_completo="Paciente Privado", psicologo=outro_psico)

        self.client.force_login(self.user)
        response = self.client.get(reverse('paciente_perfil', kwargs={'pk': paciente_alheio.pk}))

        self.assertEqual(response.status_code, 404)

    def test_template_paciente_perfil_exibe_historico_clinico_expandivel(self):
        template_path = Path(__file__).resolve().parent.parent / "templates" / "accounts" / "paciente_perfil.html"
        template_content = template_path.read_text(encoding="utf-8")

        self.assertIn("Histórico clínico", template_content)
        self.assertIn("Evoluções do paciente", template_content)
        self.assertIn("Ver completo", template_content)
        self.assertIn("truncatechars:110", template_content)

    # --- TESTES DE CADASTRO E UPDATE ---

    def test_cadastro_paciente_post_completo(self):
        self.client.force_login(self.user)
        dados = {
            'nome_completo': 'Novo Paciente',
            'email': 'paciente_novo@teste.com',
            'telefone': '11777777777',
            'data_nascimento': '1995-05-20',
            'contato_emergencia_nome': 'Maria Mãe',
            'contato_emergencia_telefone': '11666666666'
        }
        
        response = self.client.post(reverse('cadastro_paciente'), data=dados)
        self.assertEqual(response.status_code, 302)
        
        novo_p = Paciente.objects.get(nome_completo='Novo Paciente')
        self.assertEqual(novo_p.contato_emergencia_nome, 'Maria Mãe')
        self.assertIsNotNone(novo_p.usuario)
        self.assertEqual(novo_p.usuario.perfil, Usuario.Perfil.PACIENTE)
        self.assertEqual(novo_p.usuario.email, 'paciente_novo@teste.com')
        self.assertFalse(novo_p.usuario.has_usable_password())
        self.assertIsNotNone(novo_p.usuario.token_definicao_senha)
        self.assertIsNotNone(novo_p.usuario.token_definicao_senha_expira_em)
        self.assertGreater(
            novo_p.usuario.token_definicao_senha_expira_em,
            timezone.now() + timedelta(hours=47, minutes=59),
        )

    def test_update_paciente(self):
        self.client.force_login(self.user)
        url = reverse('editar_paciente', kwargs={'pk': self.paciente.pk})
        dados = {'nome_completo': 'Nome Alterado', 'email': 'novo_email@teste.com'}
        
        response = self.client.post(url, data=dados)
        self.paciente.refresh_from_db()
        self.assertEqual(self.paciente.nome_completo, 'Nome Alterado')
        
    def test_cadastro_paciente_email_invalido(self):
        self.client.force_login(self.user)
        dados = {'nome_completo': 'Teste', 'email': 'email-errado'}
        response = self.client.post(reverse('cadastro_paciente'), data=dados)
        
        self.assertEqual(response.status_code, 200)
        # Remova o hífen de "e-mail"
        self.assertFormError(response.context['form'], 'email', 'Informe um endereço de email válido.')

    def test_cadastro_paciente_bloqueia_email_ja_usado_por_usuario(self):
        Usuario.objects.create_user(
            username='jaexiste@teste.com',
            email='jaexiste@teste.com',
            password='senha123',
            perfil=Usuario.Perfil.PSICOLOGO,
        )

        self.client.force_login(self.user)
        response = self.client.post(
            reverse('cadastro_paciente'),
            data={'nome_completo': 'Paciente Repetido', 'email': 'jaexiste@teste.com'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'],
            'email',
            'Este e-mail já está em uso por outro usuário.',
        )

    def test_rota_definir_senha_paciente_existe(self):
        self.paciente.email = 'rota@teste.com'
        self.paciente.save()

        form = CadastroPacienteForm(
            instance=self.paciente,
            data={
                'nome_completo': self.paciente.nome_completo,
                'email': self.paciente.email,
            },
        )
        self.assertTrue(form.is_valid())
        paciente = form.save()

        url = reverse('definir_senha_paciente', kwargs={'token': paciente.usuario.token_definicao_senha})
        self.assertEqual(resolve(url).view_name, 'definir_senha_paciente')

    def test_definir_senha_com_token_salva_hash_e_marca_token_como_usado(self):
        self.client.force_login(self.user)
        dados = {
            'nome_completo': 'Paciente Token',
            'email': 'paciente_token@teste.com',
        }
        self.client.post(reverse('cadastro_paciente'), data=dados)

        paciente = Paciente.objects.get(email='paciente_token@teste.com')
        token = paciente.usuario.token_definicao_senha
        self.client.logout()

        response = self.client.post(
            reverse('definir_senha_paciente', kwargs={'token': token}),
            data={
                'new_password1': 'SenhaNova@123',
                'new_password2': 'SenhaNova@123',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('login'))

        paciente.usuario.refresh_from_db()
        self.assertTrue(paciente.usuario.check_password('SenhaNova@123'))
        self.assertIsNotNone(paciente.usuario.token_definicao_senha_usado_em)
        self.assertFalse(paciente.usuario.token_definicao_senha_esta_valido())

    def test_token_definicao_senha_expirado_nao_e_valido(self):
        usuario_paciente = Usuario.objects.create(
            username='paciente.expirado@teste.com',
            email='paciente.expirado@teste.com',
            nome='Paciente Expirado',
            perfil=Usuario.Perfil.PACIENTE,
        )
        usuario_paciente.set_unusable_password()
        usuario_paciente.gerar_token_definicao_senha()
        usuario_paciente.token_definicao_senha_expira_em = timezone.now() - timedelta(minutes=1)
        usuario_paciente.save()

        self.assertFalse(usuario_paciente.token_definicao_senha_esta_valido())

    # --- TESTES DE STATUS (ATIVAR/INATIVAR) ---

    def test_inativar_paciente_sucesso(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('inativar_paciente', kwargs={'pk': self.paciente.pk}))
        self.paciente.refresh_from_db()
        self.assertFalse(self.paciente.ativo)

    def test_ativar_paciente_sucesso(self):
        self.client.force_login(self.user)
        self.paciente.ativo = False
        self.paciente.save()
        
        response = self.client.get(reverse('ativar_paciente', kwargs={'pk': self.paciente.pk}))
        self.paciente.refresh_from_db()
        self.assertTrue(self.paciente.ativo)

    # --- TESTES DE VALIDAÇÃO DE FORMULÁRIO (CLEAN METHODS) ---

    def test_cadastro_psicologo_email_duplicado(self):
        url = reverse('cadastro_psicologo')
        dados = {'nome': 'Outro', 'email': 'psico1@teste.com', 'crp': '000', 'password1': '123', 'password2': '123'}
        response = self.client.post(url, data=dados)
        self.assertFormError(response.context['form'], 'email', 'E-mail já cadastrado.')

    def test_cadastro_psicologo_crp_duplicado(self):
        url = reverse('cadastro_psicologo')
        dados = {'nome': 'Outro', 'email': 'novo@email.com', 'crp': '12345', 'password1': '123', 'password2': '123'}
        response = self.client.post(url, data=dados)
        self.assertFormError(response.context['form'], 'crp', 'CRP já cadastrado.')
        
    def test_seguranca_hash_senha(self):
        user = Usuario.objects.get(email='psico1@teste.com')
        self.assertNotEqual(user.password, 'senha123')
        self.assertTrue(user.password.startswith('pbkdf2_sha256') or user.password.startswith('argon2'))
        self.assertTrue(user.check_password('senha123'))

    # --- TESTES DE SESSÃO (LOGIN/LOGOUT) ---

    def test_login_fluxo_completo(self):
        # Login
        response = self.client.post(reverse('login'), {
            'username': 'psico1@teste.com',
            'password': 'senha123'
        })
        # AJUSTE AQUI: Mude de 'pacientes_lista' para o name da sua rota de '/inicio/'
        # (Geralmente chamada de 'inicio', 'home' ou 'dashboard')
        self.assertRedirects(response, ('/inicio/'))

        # Logout
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))
        
    def test_acesso_negado_ao_dashboard_sem_login(self):
        """Testa se o redirecionamento para o login ocorre ao tentar acessar sem estar logado"""
        self.client.logout()
        response = self.client.get(reverse('pacientes_lista'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)
        
class AccountsViewsAdicionaisTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username='psico@views.com',
            email='psico@views.com',
            password='senha123',
            perfil=Usuario.Perfil.PSICOLOGO
        )
        self.psicologo = Psicologo.objects.create(usuario=self.user, crp="99999")
        self.client.force_login(self.user)

    # --- PSICÓLOGO LIST VIEW ---

    def test_psicologos_lista_retorna_200(self):
        response = self.client.get(reverse('psicologos'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('psicologos_ativos', response.context)
        self.assertIn('psicologos_inativos', response.context)

    # --- MEU PERFIL — FLUXO DO PACIENTE ---

    def test_meu_perfil_paciente_get_retorna_200(self):
        user_paciente = Usuario.objects.create_user(
            username='pac@perfil.com',
            email='pac@perfil.com',
            password='senha123',
            perfil=Usuario.Perfil.PACIENTE
        )
        paciente = Paciente.objects.create(
            nome_completo="Paciente Perfil",
            psicologo=self.psicologo,
            ativo=True,
            usuario=user_paciente
        )
        self.client.force_login(user_paciente)
        response = self.client.get(reverse('meu_perfil'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['perfil_tipo'], 'paciente')

    def test_meu_perfil_paciente_post_valido_redireciona(self):
        user_paciente = Usuario.objects.create_user(
            username='pac2@perfil.com',
            email='pac2@perfil.com',
            password='senha123',
            perfil=Usuario.Perfil.PACIENTE
        )
        paciente = Paciente.objects.create(
            nome_completo="Paciente Perfil 2",
            psicologo=self.psicologo,
            ativo=True,
            usuario=user_paciente
        )
        self.client.force_login(user_paciente)
        response = self.client.post(reverse('meu_perfil'), data={
            'nome_completo': 'Nome Atualizado',
            'email': 'pac2@perfil.com',
        })
        self.assertRedirects(response, reverse('meu_perfil'), fetch_redirect_response=False)

    def test_meu_perfil_paciente_post_invalido_retorna_200(self):
        user_paciente = Usuario.objects.create_user(
            username='pac3@perfil.com',
            email='pac3@perfil.com',
            password='senha123',
            perfil=Usuario.Perfil.PACIENTE
        )
        paciente = Paciente.objects.create(
            nome_completo="Paciente Perfil 3",
            psicologo=self.psicologo,
            ativo=True,
            usuario=user_paciente
        )
        self.client.force_login(user_paciente)
        response = self.client.post(reverse('meu_perfil'), data={
            'nome_completo': '',
            'email': 'email-invalido',
        })
        self.assertEqual(response.status_code, 200)

    # --- DEFINIR SENHA — TOKEN INVÁLIDO ---

    def test_definir_senha_token_invalido_retorna_200_com_erro(self):
        response = self.client.get(
            reverse('definir_senha_paciente', kwargs={'token': '00000000-0000-0000-0000-000000000000'})
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['token_valido'])

    def test_definir_senha_token_expirado_post_nao_salva(self):
        user_paciente = Usuario.objects.create_user(
            username='pac_exp@teste.com',
            email='pac_exp@teste.com',
            password='senha123',
            perfil=Usuario.Perfil.PACIENTE
        )
        user_paciente.gerar_token_definicao_senha()
        user_paciente.token_definicao_senha_expira_em = timezone.now() - timedelta(minutes=1)
        user_paciente.save()

        self.client.logout()
        response = self.client.post(
            reverse('definir_senha_paciente', kwargs={'token': user_paciente.token_definicao_senha}),
            data={'new_password1': 'NovaSenha@123', 'new_password2': 'NovaSenha@123'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['token_valido'])

    # --- ESQUECI SENHA ---

    def test_esqueci_senha_get_retorna_200(self):
        self.client.logout()
        response = self.client.get(reverse('esqueci_senha'))
        self.assertEqual(response.status_code, 200)

    def test_esqueci_senha_post_email_existente_redireciona(self):
        self.client.logout()
        response = self.client.post(reverse('esqueci_senha'), data={'email': 'psico@views.com'})
        self.assertRedirects(response, reverse('validar_codigo'), fetch_redirect_response=False)

    def test_esqueci_senha_post_email_inexistente_ainda_redireciona(self):
        self.client.logout()
        response = self.client.post(reverse('esqueci_senha'), data={'email': 'naoexiste@teste.com'})
        self.assertRedirects(response, reverse('validar_codigo'), fetch_redirect_response=False)

    # --- VALIDAR CÓDIGO ---

    def test_validar_codigo_sem_sessao_redireciona(self):
        self.client.logout()
        response = self.client.get(reverse('validar_codigo'))
        self.assertRedirects(response, reverse('esqueci_senha'), fetch_redirect_response=False)

    def test_validar_codigo_correto_altera_senha(self):
        self.client.logout()
        self.user.codigo_recuperacao = '123456'
        self.user.codigo_expiracao = timezone.now() + timedelta(minutes=15)
        self.user.save()

        session = self.client.session
        session['email_recuperacao'] = 'psico@views.com'
        session.save()

        response = self.client.post(reverse('validar_codigo'), data={
            'codigo': '123456',
            'nova_senha': 'NovaSenha@123'
        })
        self.assertRedirects(response, reverse('login'), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NovaSenha@123'))

    def test_validar_codigo_expirado_exibe_erro(self):
        self.client.logout()
        self.user.codigo_recuperacao = '654321'
        self.user.codigo_expiracao = timezone.now() - timedelta(minutes=1)
        self.user.save()

        session = self.client.session
        session['email_recuperacao'] = 'psico@views.com'
        session.save()

        response = self.client.post(reverse('validar_codigo'), data={
            'codigo': '654321',
            'nova_senha': 'NovaSenha@123'
        })
        self.assertEqual(response.status_code, 200)
        messages_list = list(response.context['messages'])
        self.assertTrue(any('expirou' in str(m) for m in messages_list))

    def test_validar_codigo_incorreto_exibe_erro(self):
        self.client.logout()
        self.user.codigo_recuperacao = '111111'
        self.user.codigo_expiracao = timezone.now() + timedelta(minutes=15)
        self.user.save()

        session = self.client.session
        session['email_recuperacao'] = 'psico@views.com'
        session.save()

        response = self.client.post(reverse('validar_codigo'), data={
            'codigo': '999999',
            'nova_senha': 'NovaSenha@123'
        })
        self.assertEqual(response.status_code, 200)
        messages_list = list(response.context['messages'])
        self.assertTrue(any('incorreto' in str(m) for m in messages_list))

    # --- DASHBOARD PACIENTE ---

    def test_dashboard_paciente_acesso_negado_para_psicologo(self):
        response = self.client.get(reverse('dashboard_paciente'))
        self.assertEqual(response.status_code, 403)

    def test_dashboard_paciente_acesso_permitido_para_paciente(self):
        user_paciente = Usuario.objects.create_user(
            username='pac_dash@teste.com',
            email='pac_dash@teste.com',
            password='senha123',
            perfil=Usuario.Perfil.PACIENTE
        )
        Paciente.objects.create(
            nome_completo="Paciente Dashboard",
            psicologo=self.psicologo,
            ativo=True,
            usuario=user_paciente
        )
        self.client.force_login(user_paciente)
        response = self.client.get(reverse('dashboard_paciente'))
        self.assertEqual(response.status_code, 200)

    # --- API PACIENTE HOME ---

    def test_api_paciente_home_acesso_negado_para_psicologo(self):
        response = self.client.get(reverse('api_paciente_home'))
        self.assertEqual(response.status_code, 403)

    def test_api_paciente_home_retorna_sessoes_do_paciente(self):
        import datetime
        user_paciente = Usuario.objects.create_user(
            username='pac_api@teste.com',
            email='pac_api@teste.com',
            password='senha123',
            perfil=Usuario.Perfil.PACIENTE
        )
        paciente = Paciente.objects.create(
            nome_completo="Paciente API",
            psicologo=self.psicologo,
            ativo=True,
            usuario=user_paciente
        )
        Sessao.objects.create(
            psicologo=self.psicologo,
            paciente=paciente,
            data=timezone.localdate() + datetime.timedelta(days=1),
            horario_inicio=datetime.time(10, 0),
            duracao_minutos=50,
            valor='150.00',
            status=Sessao.Status.PENDENTE,
        )
        self.client.force_login(user_paciente)
        response = self.client.get(reverse('api_paciente_home'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['tem_sessao'])
        self.assertEqual(len(data['sessoes']), 1)
