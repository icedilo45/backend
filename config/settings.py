"""
Django settings for NutriPulse / PharmaBulk.
Local: SQLite when DATABASE_URL is unset.
Production (Railway): Postgres via DATABASE_URL + gunicorn + WhiteNoise.
"""

from pathlib import Path
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

try:
    from decouple import config
except ImportError:

    def config(key, default=None, cast=None):
        val = os.getenv(key, default)
        if cast is bool and isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        if cast is not None and val is not None and val != default:
            try:
                return cast(val)
            except Exception:
                return default
        return val


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config(
    "DJANGO_SECRET_KEY",
    default="django-insecure-change-me-in-production",
)

DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

_allowed = os.getenv(
    "ALLOWED_HOSTS", "localhost,127.0.0.1,10.0.2.2,backend-production-4fb2f65f.up.railway.app"
)
ALLOWED_HOSTS = [h.strip() for h in _allowed.split(",") if h.strip()]
if DEBUG:
    ALLOWED_HOSTS = list(set(ALLOWED_HOSTS + ["*", ".ngrok-free.dev", ".ngrok.io"]))
else:
    ALLOWED_HOSTS = list(
        set(ALLOWED_HOSTS + [".up.railway.app", ".railway.app", "*"])
    )

_csrf = os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "https://backend-production-4fb2f65f.up.railway.app",
)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf.split(",") if o.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "catalog",
    "orders",
    "payments",
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

_database_url = os.getenv("DATABASE_URL", "").strip()
if _database_url:
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.config(
            default=_database_url,
            conn_max_age=600,
            # Railway internal Postgres often does not need SSL
            ssl_require=os.getenv("DB_SSL_REQUIRE", "false").lower()
            in ("true", "1", "yes"),
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Accra"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_ROOT.mkdir(parents=True, exist_ok=True)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS — native mobile apps don't need browser origins; allow all in API mode
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    _cors = os.getenv("CORS_ALLOWED_ORIGINS", "")
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors.split(",") if o.strip()]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.FirebaseAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "NutriPulse API",
    "DESCRIPTION": "Food supplement mobile pharmacy app",
    "VERSION": "0.1.0",
}

FIREBASE_CREDENTIALS_PATH = os.getenv(
    "FIREBASE_CREDENTIALS_PATH",
    str(BASE_DIR / "firebase-service-account.json"),
)
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON", "")

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY", "")
PAYSTACK_WEBHOOK_SECRET = os.getenv("PAYSTACK_WEBHOOK_SECRET", "")
PAYSTACK_CURRENCY = "GHS"

DEFAULT_DELIVERY_PROVIDER = "external_manual"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Railway terminates TLS at the edge
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "false").lower() in (
        "true",
        "1",
        "yes",
    )
