from pathlib import Path
import os
from django.contrib.messages import constants as messages

BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-f2_zmt0xg+shbbp-j+z0so7=^zuzjkg^b5i=0_h4$sofwg%xk-'

DEBUG = True

ALLOWED_HOSTS = []


# Applications
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Main App
    'classapp',
]


# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # <-- request.user exists after this
    'classapp.middleware.ActiveSessionMiddleware',             # <-- Place here!!
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'it.urls'


# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        
        # FIXED: was ("Templates "), removed the space
        'DIRS': [BASE_DIR / "Templates"],

        'APP_DIRS': True,

        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                #  Global Header Processor (categories + notifications)
                'classapp.context_processors.global_header',
            ],
        },
    },
]

WSGI_APPLICATION = 'it.wsgi.application'
ASGI_APPLICATION = "it.asgi.application"
# Channels backend
CHANNEL_LAYERS = {
  "default": {
    "BACKEND": "channels_redis.core.RedisChannelLayer",
    "CONFIG": {"hosts": [("127.0.0.1", 6379)]}
  }
}


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# DATABASES = { 
#         'default': { 
#             'ENGINE': 'django.db.backends.postgresql', 
#             'NAME': 'mentor', 
#             'USER': 'postgres', 
#             'PASSWORD': 'pass123', 
#             'HOST': 'localhost', 
#             'PORT': '5432', 
#     } 
# }


# Password Validators
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Localization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static & Media
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / 'staticfiles_build/static'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Messages
MESSAGE_TAGS = {
    messages.ERROR: 'danger'
}



# Email (SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = 'mrunalchaudhari666@gmail.com'
EMAIL_HOST_PASSWORD = 'oejagjaqkcmhpejg'
DEFAULT_FROM_EMAIL = 'MentorLMS <mrunalchaudhari666@gmail.com>'


# Email (SMTP)
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_USE_TLS = True
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_HOST_USER = 'mrunalchaudhari666@gmail.com'
# EMAIL_HOST_PASSWORD = 'oejagjaqkcmhpejg'            # App Password ONLY

# EMAIL_HOST_USER = 'akashwankhede686@gmail.com'
# EMAIL_HOST_PASSWORD = 'cdgqroxcvgfyzos'



DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", DEFAULT_FROM_EMAIL)


# Misc
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024

ADMINS = [
    ("You", "mrunalchaudhari666@gmail.com")
]

CRONJOBS = [
    ('*/15 * * * *', 'django.core.management.call_command', ['send_event_reminders'])
]


# This tells Django where to redirect for @login_required
LOGIN_URL = 'login'  

# This tells Django where to go after a successful login
LOGIN_REDIRECT_URL = 'home'  

# This tells Django where to go after logging out
LOGOUT_REDIRECT_URL = 'login'