from django.utils import timezone
from django.contrib.sessions.models import Session
from .models import UserSession


class ActiveSessionMiddleware:
    """
    Tracks active user sessions and automatically sets logout_time when:
      - Session expires
      - User closes browser
      - Django deletes session internally

    Fully compatible with Django 4.x & 5.x.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        response = self.get_response(request)

        # Only track authenticated users
        if not request.user.is_authenticated:
            return response

        session_key = request.session.session_key
        if not session_key:
            return response

        try:
            user_session = UserSession.objects.get(session_key=session_key)
        except UserSession.DoesNotExist:
            return response

        # Update last activity timestamp
        user_session.last_activity = timezone.now()
        user_session.save(update_fields=["last_activity"])

        # Check if Django session exists
        try:
            django_session = Session.objects.get(session_key=session_key)
            expiry_time = django_session.get_expiry_date()
        except Session.DoesNotExist:
            expiry_time = None

        # Case 1: Django deleted session automatically
        if expiry_time is None:
            if user_session.logout_time is None:
                user_session.logout_time = timezone.now()
                user_session.save(update_fields=["logout_time"])
            return response

        # Case 2: Session is expired
        if expiry_time < timezone.now():
            if user_session.logout_time is None:
                user_session.logout_time = timezone.now()
                user_session.save(update_fields=["logout_time"])
            return response

        return response
