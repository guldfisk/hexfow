import os

from distutils.util import strtobool

# SECRETS_PATH = os.path.join(project_name_to_secret_dir('hexfow'), 'settings.cfg')
#
# _config_parser = configparser.ConfigParser()
# _config_parser.read(SECRETS_PATH)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = "LMAOTEST"

DEBUG = strtobool(os.environ.get("DEBUG", "1"))

# ALLOWED_HOSTS = json.loads(_config_parser['default']['allowed_hosts'])
# HOST = _config_parser['default']['host']

SHELL_PLUS = "ipython"

INSTALLED_APPS = [
    # "channels",
    "daphne",
    # Local
    "frontend.apps.FrontendConfig",
    # Third-party
    "rest_framework",
    # Django
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # "debug_toolbar.middleware.DebugToolbarMiddleware",
]

ROOT_URLCONF = "hexfow.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        # 'DIRS': [BASE_DIR],
        "APP_DIRS": True,
        "OPTIONS": {
            # 'context_processors': [
            #     'django.template.context_processors.debug',
            #     'django.template.context_processors.request',
            #     'django.contrib.auth.context_processors.auth',
            #     'django.contrib.messages.context_processors.messages',
            # ],
        },
    },
]

WSGI_APPLICATION = "hexfow.wsgi.application"
ASGI_APPLICATION = "hexfow.asgi.application"

# DATABASE_NAME = 'cubespoiler'
# DATABASE_USER = 'phdk'
# DATABASE_PORT = '5432'
#
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql_psycopg2',
#         'NAME': DATABASE_NAME,
#         'USER': DATABASE_USER,
#         'PASSWORD': DATABASE_PASSWORD,
#         'HOST': DATABASE_HOST,
#         'PORT': '',
#     },
# }

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Europe/Copenhagen"
USE_TZ = True

USE_I18N = False
USE_L10N = False

STATIC_URL = '/static/'
# STATIC_ROOT = os.path.join('/', 'opt', 'services', 'hexfow', 'static')
# MEDIA_ROOT = os.path.join('/', 'opt', 'services', 'hexfow', 'media')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
    os.path.join(BASE_DIR, "frontend/build"),
]

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 50,
    # 'DEFAULT_AUTHENTICATION_CLASSES': (
    #     'knox.auth.TokenAuthentication',
    # ),
}

# if DEBUG:
#     DEBUG_TOOLBAR_CONFIG = {
#         'SHOW_TOOLBAR_CALLBACK': lambda _: False,
#         'RESULTS_CACHE_SIZE': 200,
#         'RENDER_PANELS': False,
#     }

# DEBUG_TOOLBAR_PANELS = [
#     'debug_toolbar.panels.history.HistoryPanel',
#     'debug_toolbar.panels.timer.TimerPanel',
#     'debug_toolbar.panels.headers.HeadersPanel',
#     'debug_toolbar.panels.request.RequestPanel',
#     'debug_toolbar.panels.sql.SQLPanel',
#     'debug_toolbar.panels.cache.CachePanel',
#     'debug_toolbar.panels.logging.LoggingPanel',
# ]
#
# WEBPACK_LOADER = {
#     'DEFAULT': {
#         'CACHE': not DEBUG,
#         'BUNDLE_DIR_NAME': 'bundles/',
#         'STATS_FILE': os.path.join(BASE_DIR, 'webpack-stats.json'),
#         'POLL_INTERVAL': 0.1,
#         'TIMEOUT': None,
#         'IGNORE': [r'.+\.hot-update.js', r'.+\.map'],
#         'LOADER_CLASS': 'webpack_loader.loader.WebpackLoader',
#     }
# }

# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'handlers': {
#         'console': {
#             'class': 'logging.StreamHandler',
#         },
#     },
#     'root': {
#         'handlers': ['console'],
#         'level': 'DEBUG',
#     },
# }
