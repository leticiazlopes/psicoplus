# Psico+ 🧠

O Psico+ é um sistema de gestão clínica desenhado especificamente para psicólogos. O foco principal do projeto é a **segurança de dados**, a **privacidade dos pacientes** e a **rastreabilidade das informações**, utilizando as melhores práticas de desenvolvimento com o framework Django.

![Django](https://img.shields.io/badge/Django-4.2-092e20?style=for-the-badge&logo=django)
![Python](https://img.shields.io/badge/Python-3.9-3776ab?style=for-the-badge&logo=python)
![Coverage](https://img.shields.io/badge/Coverage-75%25-yellow?style=for-the-badge)
![Status](https://img.shields.io/badge/Sprint-4%20of%205-success?style=for-the-badge)
![Status](https://img.shields.io/badge/Ciclo-4%20(Finalização)-orange?style=for-the-badge)

---

## 🚀 Funcionalidades Atuais

- **Autenticação Segura:** Sistema de login/logout com proteção contra acessos indevidos (POST logout), recuperação de senha e perfis diferenciados para psicólogos e pacientes.
- **Gestão de Psicólogos:** Cadastro com validação de CRP, isolamento de perfil e painel de controle exclusivo.
- **Gestão de Pacientes (CRUD):** Registro completo de dados pessoais, contatos de emergência e histórico de atendimento.
  - **Paginação Dinâmica:** Implementação de paginação estruturada nas views de listagem para limitar a exibição de registros por página (ex: limite de 10 itens), com botões de navegação ("Anterior", "Próxima" e indicador de página) renderizados com Tailwind CSS no rodapé.
  - **Preservação de Filtros:** Garantia de que parâmetros e filtros ativos na URL (como busca por data) não sejam perdidos ou resetados ao mudar de página.
  - **Interface Amigável e Edição:** Edição fluida e inativação de registros (Soft Delete).
- **Agenda de Sessões:** Agendamento de sessões, séries recorrentes, edição e cancelamento de compromissos.
- **Diário de Pensamentos do Paciente (US-13):** Módulo completo de automonitoramento focado na experiência do paciente.
  - **Modelagem de Dados:** Estrutura de banco de dados desenhada especificamente para armazenar os registros do diário.
  - **Histórico Rastreável:** Exibição de listagem de registros salvos contendo data e hora precisas.
  - **Interface de Registro (Front-end):** Tela interativa adaptada para a inserção de pensamentos correlacionados com campos de seleção de emoção e intensidade.
- **Segurança e Regras Clínicas (Melhorias e Ajustes):**
  - **Trava de Segurança Clínica:** O sistema impede estritamente que uma sessão seja marcada como falta, pendente ou cancelada caso já exista um prontuário eletrônico emitido e vinculado a ela.
  - **Mechanics e Dependências:** Resolução de quebras críticas de ambiente através da correção da versão do `pycparser` no arquivo `requirements.txt`.
- **Internacionalização e Tradução (i18n):** Sistema totalmente preparado para suporte multi-idiomas.
  - Validação de variáveis críticas de localização no arquivo `settings.py` (`USE_I18N = True`, `USE_TZ = True` e `LANGUAGE_CODE = 'pt-br'`).
  - Inclusão da tag `{% load i18n %}` no topo dos templates base e isolamento de textos estáticos sensíveis com a tag `{% trans "Texto" %}`.
  - Internacionalização completa aplicada diretamente em views, models e formulários das páginas internas do ecossistema.

---

## 🧪 Qualidade de Código e Testes

O projeto conta com uma suíte de testes automatizados utilizando `pytest` e `unittest`, atingindo atualmente **75% de cobertura**.

### Áreas Cobertas:
- **Models:** Validação de campos, integridade, relacionamentos e regras de dados do Diário de Pensamentos.
- **Forms:** Lógica de limpeza de dados (`clean_methods`), internacionalização de labels e validações de duplicidade.
- **Views:** Testes de fluxo de sucesso, paginação com query strings preservadas, tratamento de erros e permissões.
- **Security:** Verificação de hashing de passwords, proteção contra acessos indevidos e isolamento de rotas.
- **Testes Unitários Dedicados:** Escrita de testes unitários específicos para validar as regras da US-13 (Diário de Pensamentos).

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



---

## 📈 Histórico de Ciclos

| Ciclo | Sprint | Status | Principais Entregas |
| --- | --- | --- | --- |
| **1** | **S1** | ✅ Concluído | Auth, Cadastro de Psicólogo e CRUD de Pacientes. |
| **2** | **S2** | ✅ Concluído | Gestão de Agenda e Horários. |
| **3** | **S3** | ✅ Concluído | Módulo de Prontuários Eletrônicos e Prontuário Estruturado. |
| **4** | **S4** | 🏁 Finalizando | Diário de Pensamentos do Paciente (US-13), Suporte Completo à Internacionalização (i18n), Paginação da Listagem com Retenção de Filtros e Ajustes de Regras Clínicas. |
| 5 | S5 | ⏳ Planejado | Módulo Financeiro, Dashboards e Deploy Final. |