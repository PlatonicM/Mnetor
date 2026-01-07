from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

from classapp.models import (
    Event,
    EventRegistration,
    WaitlistEntry,
    InstructorProfile
)


class Command(BaseCommand):
    help = "Hourly event scheduler: reminders, waitlist → confirmed promotion, and join links."

    def send_email(self, subject, text_body, html_body, recipient):
        """Send both HTML + plain mail."""
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient]
        )
        if html_body:
            msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=True)

    def handle(self, *args, **options):
        now = timezone.now()

        # 1️⃣ REMINDERS → Events starting within next 24 hours
        in_24 = now + timezone.timedelta(hours=24)

        upcoming_events = Event.objects.filter(
            status="PUBLISHED",
            start__gte=now,
            start__lt=in_24
        )

        for event in upcoming_events:
            join_link = f"{settings.SITE_URL}/events/{event.id}/join/"

            registrations = EventRegistration.objects.filter(
                event=event,
                status="CONFIRMED"
            )

            for reg in registrations:
                recipient_email = reg.email  
                participant_name = reg.full_name or "Participant"

                subject = f"Reminder: Your event '{event.title}' starts soon"
                text_body = (
                    f"Hi {participant_name},\n\n"
                    f"This is a reminder that your event '{event.title}' "
                    f"starts at {event.start}.\n\n"
                    f"Join using this link: {join_link}"
                )
                html_body = f"""
                <p>Hi <strong>{participant_name}</strong>,</p>
                <p>Your registered event <strong>{event.title}</strong> starts soon.</p>
                <p><b>Start Time:</b> {event.start}</p>
                <p><a href="{join_link}" 
                    style="padding:10px 20px;background:#2563eb;color:#fff;
                            text-decoration:none;border-radius:6px;">
                    Join Event
                </a></p>
                """

                self.send_email(subject, text_body, html_body, recipient_email)

            # Event instructors / mentors also get reminder
            if event.instructor:
                instructor_email = event.instructor.user.email
                subject = f"Mentor Reminder: '{event.title}' starts soon"
                html_body = f"""
                <p>Hello Mentor <strong>{event.instructor.user.username}</strong>,</p>
                <p>Your event <strong>{event.title}</strong> is starting soon.</p>
                <p><b>Start Time:</b> {event.start}</p>
                <p><a href="{join_link}" 
                    style="padding:10px 20px;background:#16a34a;color:#fff;
                            text-decoration:none;border-radius:6px;">
                    Join Event
                </a></p>
                """
                self.send_email(subject, subject, html_body, instructor_email)

        # 2️⃣ WAITLIST → Promote to confirmed if seats available
        live_events = Event.objects.filter(status="PUBLISHED")

        for event in live_events:
            if event.capacity == 0:
                continue

            seats_left = event.seats_left
            if not seats_left or seats_left <= 0:
                continue

            # Promote exact number of people
            waitlist = WaitlistEntry.objects.filter(
                event=event, notified=False
            ).order_by("created_at")[:seats_left]

            for entry in waitlist:
                # Create automatic confirmed registration
                EventRegistration.objects.create(
                    event=event,
                    first_name=entry.name.split(" ")[0],
                    last_name=" ".join(entry.name.split(" ")[1:]),
                    email=entry.email,
                    status="CONFIRMED",
                    confirmed_at=timezone.now(),
                )

                entry.notified = True
                entry.save()

                join_link = f"{settings.SITE_URL}/events/{event.id}/join/"

                subject = f"You have a seat in '{event.title}'!"
                text_body = (
                    f"Good news! You have been promoted from waitlist "
                    f"to confirmed attendee for '{event.title}'.\n\n"
                    f"Join link: {join_link}"
                )
                html_body = f"""
                <p>Good news <strong>{entry.name}</strong>!</p>
                <p>You are now confirmed for the event <strong>{event.title}</strong>.</p>
                <p><a href="{join_link}"
                    style="padding:10px 20px;background:#3b82f6;color:#fff;
                            border-radius:6px;text-decoration:none;">
                    Join Event
                </a></p>
                """

                self.send_email(subject, text_body, html_body, entry.email)

        self.stdout.write("✔ Event reminders & waitlist promotions executed.")
