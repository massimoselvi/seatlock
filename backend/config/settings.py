from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR.parent / ".env")

INSECURE_DEV_KEY = "dev-insecure-change-me"
DEBUG = env("DEBUG")
SECRET_KEY = env("SECRET_KEY", default=INSECURE_DEV_KEY)
if not DEBUG and SECRET_KEY == INSECURE_DEV_KEY:
    # Fail closed: a task that lost its secret must not start with a public key.
    raise ImproperlyConfigured("SECRET_KEY must be set when DEBUG is off.")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "web"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "infrastructure.db",  # label "workshops": keeps table names and migration history
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://seatlock:seatlock@localhost:5432/seatlock",
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "interface.api.accounts.authentication.ExpiringTokenAuthentication"
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    # Number of proxies in front of the app, so DRF reads the real client IP from the right end
    # of X-Forwarded-For. 0 means "trust only the socket address". ECS sets 2: CloudFront, ALB.
    "NUM_PROXIES": env.int("NUM_PROXIES", default=0),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "120/min",
        # Seat-changing endpoints are the expensive ones: they take a row lock.
        "registration": "10/min",
        "auth": "10/min",
        "login": "10/min",
        "login_user": "10/min",
    },
}

# Production answers JSON only. The browsable API is for local development.
if not DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = ["rest_framework.renderers.JSONRenderer"]

# API tokens stop working after this many hours. Signing in again issues a new one.
AUTH_TOKEN_TTL_HOURS = env.int("AUTH_TOKEN_TTL_HOURS", default=24 * 7)

# Redis backs the cache so throttle counters and cached lists are shared by all web workers.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("CACHE_URL", default="redis://localhost:6379/1"),
    }
}
WORKSHOP_LIST_CACHE_SECONDS = env.int("WORKSHOP_LIST_CACHE_SECONDS", default=30)

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
# Repairs promotions lost between a commit and the enqueue (ADR 0002). Safe to run twice.
CELERY_BEAT_SCHEDULE = {
    "sweep-waitlists": {
        "task": "workshops.tasks.sweep_waitlists",
        "schedule": env.int("WAITLIST_SWEEP_SECONDS", default=300),
    }
}

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = "Seatlock <noreply@seatlock.local>"

# Production hardening. Cookies are only used by the admin, but they must never travel over HTTP.
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# Turn on once every hop to the app carries HTTPS. Behind CloudFront and an HTTP-only ALB the
# proxy header always says "http", so enabling this too early causes a redirect loop (issue #47).
FORCE_HTTPS = env.bool("FORCE_HTTPS", default=False)
if FORCE_HTTPS:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^api/health/$"]  # the ALB health check speaks plain HTTP
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # Preloading is hard to undo and needs an owned domain. Decide that on purpose, later.
    SILENCED_SYSTEM_CHECKS = ["security.W021"]

# The Django admin is for local use. Production turns it off (and the ALB blocks /admin too).
ADMIN_ENABLED = env.bool("ADMIN_ENABLED", default=True)
