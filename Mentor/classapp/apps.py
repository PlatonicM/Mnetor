from django.apps import AppConfig

def patch_mongodb_objectid_fields():
    try:
        from django_mongodb_backend.fields import ObjectIdAutoField, ObjectIdField
        from bson.errors import InvalidId

        def safe_to_python(orig_func):
            def inner(self, value):
                if value in (None, 'None', 'null', ''):
                    return None
                try:
                    return orig_func(self, value)
                except (InvalidId, Exception):
                    return None
            return inner

        if not getattr(ObjectIdAutoField, '_patched_safe', False):
            ObjectIdAutoField.to_python = safe_to_python(ObjectIdAutoField.to_python)
            ObjectIdAutoField._patched_safe = True

        if not getattr(ObjectIdField, '_patched_safe', False):
            ObjectIdField.to_python = safe_to_python(ObjectIdField.to_python)
            ObjectIdField._patched_safe = True
    except Exception:
        pass

def patch_mongo_pk(model):
    try:
        from django_mongodb_backend.fields import ObjectIdAutoField
        old_field = model._meta.get_field('id')
        if not isinstance(old_field, ObjectIdAutoField):
            model._meta.local_fields.remove(old_field)
            model._meta.auto_field = None
            model._meta.pk = None
            new_field = ObjectIdAutoField(primary_key=True, db_column='_id')
            new_field.contribute_to_class(model, 'id')
    except Exception:
        pass

try:
    import django_mongodb_backend
    DEFAULT_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'
except ImportError:
    DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

class ClassappConfig(AppConfig):
    default_auto_field = DEFAULT_AUTO_FIELD
    name = 'classapp'

    def ready(self):
        patch_mongodb_objectid_fields()

        # Patch built-in Django models for MongoDB ObjectId primary keys
        from django.contrib.auth.models import User, Group, Permission
        from django.contrib.contenttypes.models import ContentType
        from django.contrib.admin.models import LogEntry

        for model in [User, Group, Permission, ContentType, LogEntry]:
            patch_mongo_pk(model)

        try:
            from django.contrib.auth.models import update_last_login
            from django.contrib.auth.signals import user_logged_in
            user_logged_in.disconnect(update_last_login)
        except Exception:
            pass

        # import signals to register them
        from . import signals  # noqa


