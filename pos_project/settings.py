"""
Django settings for pos_project project.
Updated for KOSHUR POS Branding - Saffron & Chinar Theme
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-nj0b6cm#zcc!wjkkg5_#z$2j+wk5v--68j-q94#00ih$ian^9x'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*'] 

# Application definition
INSTALLED_APPS = [
    'jazzmin',  # Must stay at the top
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'pos', 
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'pos_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'pos_project.wsgi.application'

# Database - PostgreSQL Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'restaurant_pos',
        'USER': 'postgres',
        'PASSWORD': 'Zakir@1326', 
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# --- JAZZMIN SETTINGS (KOSHUR POS BRANDING) ---
JAZZMIN_SETTINGS = {
    "site_title": "Koshur POS Admin",
    "site_header": "Koshur POS",
    "site_brand": "KOSHUR POS",
    "welcome_sign": "Welcome to KOSHUR POS Management Hub",
    "copyright": "Koshur POS Systems Ltd",
    
    # CRITICAL: This links your new external CSS file to "Vanish the Green"
    "custom_css": "admin/css/koshur_theme.css",
    
    "topmenu_links": [
        {"name": "Live Floor", "url": "/table/", "new_window": False, "icon": "fas fa-desktop"},
        {"name": "Sales Hub", "url": "/admin/dashboard/", "icon": "fas fa-chart-line"},
    ],

    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": ["auth"], 
    
    "icons": {
        "pos.Restaurant": "fas fa-store",
        "pos.Table": "fas fa-chair",
        "pos.Category": "fas fa-tags",
        "pos.MenuItem": "fas fa-utensils",
        "pos.MenuVariant": "fas fa-rupee-sign",
        "pos.Order": "fas fa-shopping-cart",
        "pos.OrderItem": "fas fa-list-ul",
        "pos.Expense": "fas fa-money-bill-wave",
    },
    
    "order_with_respect_to": ["pos.Table", "pos.Order", "pos.MenuItem", "pos.Category"],
    "related_modal_active": True,
}

# --- JAZZMIN UI TWEAKS (The Saffron Theme) ---
JAZZMIN_UI_TWEAKS = {
    "theme": "default", 
    "navbar": "navbar-dark bg-dark",
    "accent": "accent-orange",        # Saffron Accents
    "navbar_fixed": True,
    "container_layout": "fullwidth",
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-warning", # Sidebar highlights in Saffron
    "sidebar_nav_child_indent": True,
    "button_classes": {
        "primary": "btn-warning",     # Main buttons become Saffron
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-warning"      # Forces "Available" badges to be Saffron
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization (IST for India)
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# --- STATIC FILES CONFIGURATION ---
STATIC_URL = 'static/'
# This tells Django to look for your 'static' folder in the root directory
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'