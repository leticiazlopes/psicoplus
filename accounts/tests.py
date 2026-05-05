from django.test import TestCase
from django.urls import reverse
from .models import Usuario, Psicologo, Paciente

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
        self.assertRedirects(response, reverse('pacientes_lista'))

        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))
        
    def test_acesso_negado_ao_dashboard_sem_login(self):
        """Testa se o redirecionamento para o login ocorre ao tentar acessar sem estar logado"""
        self.client.logout()
        response = self.client.get(reverse('pacientes_lista'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)
        
    