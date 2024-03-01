from django.apps import AppConfig


class DjangoapiConfig(AppConfig):
    name = 'djangoAPI'


class UsersConfig(AppConfig):
    name = 'users'
    default_auto_field = 'django.db.models.BigAutoField'
