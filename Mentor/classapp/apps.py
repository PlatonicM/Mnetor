from django.apps import AppConfig

class ClassappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'classapp'

    def ready(self):
        # import signals to register them
        from . import signals  # noqa
