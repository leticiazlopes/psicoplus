
# Psico+ 🧠

O Psico+ é um sistema de gestão clínica desenhado especificamente para psicólogos. O foco principal do projeto é a **segurança de dados**, a **privacidade dos pacientes** e a **rastreabilidade das informações**, utilizando as melhores práticas de desenvolvimento com o framework Django.

![Django](https://img.shields.io/badge/Django-4.2-092e20?style=for-the-badge&logo=django)
![Python](https://img.shields.io/badge/Python-3.9-3776ab?style=for-the-badge&logo=python)
![Coverage](https://img.shields.io/badge/Coverage-75%25-yellow?style=for-the-badge)
![Status](https://img.shields.io/badge/Sprint-2%20of%205-success?style=for-the-badge)
![Status](https://img.shields.io/badge/Ciclo-2%20(Entrega)-orange?style=for-the-badge)

---

## 🚀 Funcionalidades Atuais

- **Autenticação Segura:** Sistema de login/logout com proteção contra acessos indevidos (POST logout), recuperação de senha e perfis diferenciados para psicólogos e pacientes.
- **Gestão de Psicólogos:** Cadastro com validação de CRP, isolamento de perfil e painel de controle exclusivo.
- **Gestão de Pacientes (CRUD):** Registro completo de dados pessoais, contatos de emergência e histórico de atendimento.
  - Listagem com filtros de busca dinâmica.
  - Edição via interface amigável.
  - Inativação de registros (Soft Delete).
- **Agenda de Sessões:** agendamento de sessões, séries recorrentes, edição e cancelamento de compromissos.
- **Histórico de Status:** registro automático de alterações de status de sessão para rastreabilidade clínica.
---

## 🧪 Qualidade de Código e Testes

O projeto conta com uma suite de testes automatizados utilizando `pytest` e `unittest`, atingindo atualmente **75% de cobertura**.

### Áreas Cobertas:
- **Models:** Validação de campos, integridade e relacionamentos.
- **Forms:** Lógica de limpeza de dados (`clean_methods`) e validações de duplicidade.
- **Views:** Testes de fluxo de sucesso, falha de validação e permissões de acesso.
- **Security:** Verificação de hashing de passwords e proteção de rotas.

---

## ⚙️ Instalação e Execução

1. **Clonar o Repositório:**
   ```bash
   git clone [https://github.com/leticiazlopes/psicoplus.git](https://github.com/leticiazlopes/psicoplus.git)
   cd psicoplus
   ```

2. **Configurar Ambiente Virtual:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   # venv\Scripts\activate   # Windows
   ```

3. **Instalar Dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Migrações e Servidor:**
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

## 🧪 Testes

1. Ative o ambiente virtual:
   ```bash
   source venv/bin/activate  # macOS/Linux
   # venv\Scripts\activate   # Windows
   ```
2. Execute a suíte de testes Django:
   ```bash
   python manage.py test
   ```
3. Se quiser gerar relatório de cobertura:
   ```bash
   coverage run manage.py test
   coverage html
   ```

## 📈 Histórico de Ciclos

| Ciclo | Sprint | Status | Principais Entregas |
| :--- | :--- | :--- | :--- |
| **1** | **S1** | ✅ Concluído | Auth, Cadastro de Psicólogo e CRUD de Pacientes. |
| **2** | **S2** | ✅ Concluído | Gestão de Agenda e Horários. |
| 3 | S3 | ⏳ Planejado | Módulo de Prontuários Eletrônicos. |
| 4 | S4 | ⏳ Planejado | Controle Financeiro. |
| 5 | S5 | ⏳ Planejado | Dashboards e Deploy Final. |