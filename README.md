Aqui tens o conteúdo do ficheiro `README.md` estruturado de forma profissional, destacando a qualidade técnica e os resultados de cobertura que alcançaste.

```markdown
# Psico+ 🧠

O Psico+ é um sistema de gestão clínica desenhado especificamente para psicólogos. O foco principal do projeto é a **segurança de dados**, a **privacidade dos pacientes** e a **rastreabilidade das informações**, utilizando as melhores práticas de desenvolvimento com o framework Django.

![Django](https://img.shields.io/badge/Django-4.2-092e20?style=for-the-badge&logo=django)
![Python](https://img.shields.io/badge/Python-3.9-3776ab?style=for-the-badge&logo=python)
![Coverage](https://img.shields.io/badge/Coverage-91%25-brightgreen?style=for-the-badge)

---

## 🚀 Funcionalidades Atuais

- **Autenticação Segura:** Sistema de login/logout com proteção contra acessos indevidos (POST logout).
- **Gestão de Psicólogos:** Cadastro com validação de CRP e isolamento de perfil.
- **Gestão de Pacientes (CRUD):** - Registo completo (Dados pessoais e contactos de emergência).
  - Listagem com filtros de busca dinâmica.
  - Edição via interface amigável.
  - Inativação de registos (Soft Delete).
- **Segurança de Acesso:** Handlers customizados para erros 404 e 405, garantindo que o utilizador nunca veja páginas técnicas do servidor.

---

## 🛡️ Decisões de Arquitetura

### 1. Identificadores Únicos (UUID)
Para evitar que IDs sequenciais sejam expostos nas URLs (o que facilitaria ataques de enumeração), todos os modelos utilizam **UUID v4** como chave primária.

### 2. Autenticação Stateful
O projeto utiliza o sistema de sessões nativo do Django com proteção **CSRF (Cross-Site Request Forgery)**, ideal para aplicações que utilizam Django Templates, garantindo segurança robusta sem a complexidade desnecessária de JWT para este cenário.

### 3. Isolamento de Dados
Implementada lógica de filtragem ao nível do QuerySet, garantindo que um psicólogo **apenas** consiga visualizar, editar ou remover os seus próprios pacientes.

---

## 🧪 Qualidade de Código e Testes

O projeto conta com uma suite de testes automatizados utilizando `pytest` e `unittest`, atingindo atualmente **91% de cobertura**.

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

---

## 📊 Relatório de Cobertura (Coverage)

Para gerar o relatório de cobertura atualizado:

```bash
coverage run -m pytest
coverage report
```

| Módulo | Cobertura |
| :--- | :--- |
| `accounts/models.py` | 93% |
| `accounts/views.py` | 91% |
| `accounts/forms.py` | 84% |
| **TOTAL** | **91%** |
```