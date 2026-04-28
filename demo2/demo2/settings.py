"""
Django settings for demo2 project.
"""

from pathlib import Path

import django_ip_safeguard

BASE_DIR = Path(__file__).resolve().parent.parent
# 无论 pip 安装还是源码目录，locale 均在包内（勿写死仓库相对路径）
_PLUGIN_ROOT = Path(django_ip_safeguard.__file__).resolve().parent

SECRET_KEY = 'django-insecure-35m(74*8@-o8!hb_45e%m57p&a_*7xuebfbt0ykg#jd%1bx6s9'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_ip_safeguard',
    'unfold',
    'unfold.contrib.filters',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_ip_safeguard.middleware.IpGuardMiddleware',
]

ROOT_URLCONF = 'demo2.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'demo2.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOCALE_PATHS = [
    _PLUGIN_ROOT / 'locale',
]

# 本地联调：浏览器访问 8000、可选 Vite 5173 等
CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://127.0.0.1:5173',
    'http://localhost:5173',
]

# 可与扁平项 IP_GUARD_* 混用；扁平项存在时优先于本字典同义键（见 django_ip_safeguard.conf.get_settings）
IP_GUARD = {
    'ENABLED': True,
    'WHITELIST_IPS': ['127.0.0.1', 'localhost'],
    'DEFAULT_POLICY': 'allow',
    'JWT': {
        'SECRET_KEY': 'demo2-secret-key-change-in-production',
        'ACCESS_TOKEN_LIFETIME_MINUTES': 60,
        'REFRESH_TOKEN_LIFETIME_DAYS': 7,
    },
    'CACHE': {
        'ENABLED': False,
    },
}
