from django.dispatch import receiver
from django.utils.crypto import get_random_string
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models.signals import post_save
from django.core.mail import mail_admins
from django.contrib.auth.signals import user_logged_in, user_logged_out

from .models import (
    Order,
    OrderItem,
    Invoice,
    MyCourse,
    CartItem,
    LoginActivity,
    UserSession,
    KYCDocument,
)


# UTIL – Proper IP extraction
def get_client_ip(request):
    """
    Get the client IP address, supporting setups behind reverse proxies.
    Looks at X-Forwarded-For first, then REMOTE_ADDR.
    """
    if not request:
        return None

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        # X-Forwarded-For: client, proxy1, proxy2,...
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


# 1) ORDER STATUS → AUTO COURSE ENROLLMENT + CART CLEAR + INVOICE
@receiver(post_save, sender=Order)
def order_post_save(sender, instance: Order, created, **kwargs):
    """
    Triggered whenever an Order is saved.

    If order is PAID:
        ✔ Enrolls user in purchased courses (MyCourse)
        ✔ Removes purchased courses from the user's cart
        ✔ Generates an Invoice (if not already created)
    """

    # Only act when payment is completed
    if instance.status != "PAID":
        return

    user = instance.user

    # Enroll in all purchased courses
    for item in instance.items.all():
        # Ensure the user is enrolled only once per course
        MyCourse.objects.get_or_create(
            user=user,
            course=item.course,
            defaults={
                "progress": 0,
                "rating": 0,
                "lesson_count": 0,
                "completed_lessons": [],
            },
        )
        # Remove from cart
        CartItem.objects.filter(user=user, course=item.course).delete()

    # Auto-generate invoice once per order
    if not hasattr(instance, "invoice"):
        inv_no = f"INV-{get_random_string(10).upper()}"

        invoice = Invoice.objects.create(
            order=instance,
            invoice_number=inv_no,
        )

        # OPTIONAL: PDF generation (enable when you add a PDF engine)
        # html = render_to_string("invoice_template.html", {"order": instance})
        # pdf_bytes = generate_pdf_from_html(html)
        # invoice.pdf_file.save(f"{inv_no}.pdf", ContentFile(pdf_bytes))
        # invoice.save()


# 2) USER LOGIN TRACKING
@receiver(user_logged_in)
def track_login(sender, request, user, **kwargs):
    """
    Tracks:
        ✔ Login history (LoginActivity)
        ✔ Active user session (UserSession)

    This works together with ensure_session_key(request) in your login view.
    """

    if not request:
        return

    # Extra safety: if session_key is missing, create a session
    if not request.session.session_key:
        request.session.create()

    ip = get_client_ip(request)
    ua = request.META.get("HTTP_USER_AGENT", "")
    session_key = request.session.session_key

    # Create login history row
    LoginActivity.objects.create(
        user=user,
        ip_address=ip,
        user_agent=ua,
        login_time=timezone.now(),
    )

    # Track / upsert active session
    UserSession.objects.update_or_create(
        session_key=session_key,
        defaults={
            "user": user,
            "ip_address": ip,
            "user_agent": ua,
            "login_time": timezone.now(),
            "last_activity": timezone.now(),
        },
    )


# 3) USER LOGOUT TRACKING
@receiver(user_logged_out)
def track_logout(sender, request, user, **kwargs):
    """
    Sets logout_time on the active session for this request.
    Does nothing if the session record is missing.
    """

    if not request:
        return

    session_key = request.session.session_key
    if not session_key:
        return

    try:
        session = UserSession.objects.get(session_key=session_key)
        session.logout_time = timezone.now()
        session.save(update_fields=["logout_time"])
    except UserSession.DoesNotExist:
        pass


# 4) KYC ADMIN NOTIFICATION
@receiver(post_save, sender=KYCDocument)
def notify_admin_on_kyc(sender, instance, created, **kwargs):
    """
    When a new KYCDocument is created with status=PENDING,
    send an email notification to site admins (settings.ADMINS).
    """
    if created and instance.status == "PENDING":
        subject = f"New KYC Submitted: {instance.user.username}"
        message = (
            f"User: {instance.user.username}\n"
            f"Document Type: {instance.get_doc_type_display()}\n\n"
            "A new KYC document awaits review."
        )

        try:
            mail_admins(subject, message)
        except Exception:
            # Fail silently so that KYC creation doesn't crash the request
            pass
