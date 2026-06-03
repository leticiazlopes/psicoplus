import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega o arquivo .env local automaticamente se ele existir
load_dotenv(os.path.join(BASE_DIR, '.env'))

# QUICK-START DEVELOPMENT SETTINGS
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'uma-chave-padrao-temporaria')

# Se DJANGO_DEBUG=True estiver no .env, vira True. Caso contrário, vira False (Produção).
DEBUG = os.getenv('DJANGO_DEBUG', 'False') == 'True'

ALLOWED_HOSTS = ['*']


# APPLICATION DEFINITION
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'agenda',
    'atendimentos',
    'dashboard',
    'anymail',
]

AUTH_USER_MODEL = 'accounts.Usuario' 

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'psicoplus.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        "DIRS": [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'psicoplus.wsgi.application'


# DATABASE CONFIGURATION
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Se existe DATABASE_URL (Produção no Render / Postgres)
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=True
        )
    }
else:
    # Fallback estrito para SQLite (Desenvolvimento local e CI/CD)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# PASSWORD VALIDATION
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# INTERNATIONALIZATION
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True


# STATIC FILES (CSS, JAVASCRIPT, IMAGES)
STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / 'staticfiles'

# Escolhe o armazenamento certo dependendo do ambiente (Local vs Render)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG else "whitenoise.storage.CompressedStaticFilesStorage",
    },
}


# REDIRECTION & LOGINS
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGOUT_REDIRECT_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGIN_URL = 'login'


# ==============================================================================
# EMAIL CONFIGURATION (Dinamizado para Dev e Produção)
# ==============================================================================
if DEBUG:
    # Em desenvolvimento, exibe o e-mail diretamente no terminal do VS Code/Terminal
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'Equipe Psico+ <teste@psicoplus.com>'
else:
    # Em produção (Render), usa a API do Brevo de forma estrita
    EMAIL_BACKEND = 'anymail.backends.brevo.EmailBackend'
    
    # Resgate seguro com fallback caso a variável do Render suma por um instante
    EMAIL_REMOCAO_ERRO = os.getenv('EMAIL_USER', 'suportepsicoplus@gmail.com')
    DEFAULT_FROM_EMAIL = f"Equipe Psico+ <{EMAIL_REMOCAO_ERRO}>"

    # O dicionário ANYMAIL deve existir EXCLUSIVAMENTE em produção
    ANYMAIL = {
        "BREVO_API_KEY": os.getenv("BREVO_API_KEY"),
    }

# CONFIGURAÇÕES DE SEGURANÇA ADICIONAIS PARA PRODUÇÃO
if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_TRUSTED_ORIGINS = [
    'https://psicoplus.onrender.com',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]