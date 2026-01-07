from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import UserSession

User = get_user_model()


class ActiveSessionMiddleware(MiddlewareMixin):
    """
    Tracks authenticated user sessions.
    Creates a UserSession on login and updates last_activity.
    Automatically sets logout_time when session expires or inactivity detected.
    """

    INACTIVITY_LIMIT = 60 * 10   # 10 minutes (you can change)

    def process_request(self, request):
        if not request.user.is_authenticated:
            return

        # Ensure session key exists
        session_key = request.session.session_key
        if not session_key:
            request.session.save()
            session_key = request.session.session_key

        # Get or create the session record
        session_obj, created = UserSession.objects.get_or_create(
            session_key=session_key,
            defaults={
                "user": request.user,
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                "ip_address": request.META.get("REMOTE_ADDR", ""),
                "login_time": timezone.now(),
                "last_activity": timezone.now(),
            }
        )

        # Already existed → update only activity (NOT logout time)
        if not created:
            now = timezone.now()

            # Check inactivity limit to auto-set logout_time
            if (
                session_obj.last_activity
                and (now - session_obj.last_activity).total_seconds() > self.INACTIVITY_LIMIT
                and session_obj.logout_time is None
            ):
                session_obj.logout_time = now

            # update last activity always
            session_obj.last_activity = now
            session_obj.user = request.user
            session_obj.save(update_fields=["last_activity", "user", "logout_time"])

    def process_response(self, request, response):
        """
        Do NOT write logout time on every request.
        Logout time is only updated by Django's logout view or inactivity timeout.
        """
        return response
