import time
import uuid
from bson import ObjectId
from io import BytesIO
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone 
from django.contrib import messages    
from django.db.models import Sum, Count, F
from .forms import SubscribeForm, KYCDocumentForm
from django.core.mail import send_mail, BadHeaderError
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from .models import Courses, MyCourse, CourseRating, SubscriberEmail, ContactMessage, KYCDocument
from django.views.decorators.http import require_GET, require_POST
from django.utils.timesince import timesince
from django.urls import reverse
from django.core.paginator import Paginator
from .models import Category, Notification, Order, Event, Certificate, EventCategory, Speaker, WaitlistEntry, InstructorProfile, Courses, InstructorReview, LessonComplete, MyCourse, EventRegistration, SubscriberEmail
#from .forms import InstructorReviewForm
try:
    from weasyprint import HTML
except ImportError:
    HTML = None
from django.contrib.auth import update_session_auth_hash
from django.db import transaction
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from django.db import transaction
from django.views.decorators.cache import never_cache


# SIMPLE RATE-LIMIT DICT (IP: timestamp)
RATE_LIMIT = {}

# PDF libs
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

from .models import (
    Courses, Lesson, MyCourse, CartItem, CourseRating,
    Order, OrderItem, Invoice, InstructorProfile, LoginActivity, UserSession, EventRegistration
)
from .forms import SignupForm, LoginForm, ProfileForm, InstructorProfileForm, ChangePasswordForm


#-------------------------------START---------------------------------------------------------

User = get_user_model()

# HOME
# def home(request):
#     courses = Courses.objects.all()
#     return render(request, "home.html", {"courses": courses})


# views.py (Update your home view)
from .models import Certificate

def home(request):
    try:
        db_courses = list(Courses.objects.all().order_by('-id')[:6])
    except Exception:
        db_courses = []

    # 6 Curated High-Impact Top Featured Tracks for Home Hero Grid
    featured_6 = [
        {"id": 101, "name": "Full-Stack React & Node.js Architecture Masterclass", "category": "Software Engineering", "price": 4999, "instructor": "Alex Chen", "image_url": "https://images.unsplash.com/photo-1633356122544-f134324a6cee?auto=format&fit=crop&w=600&q=80"},
        {"id": 201, "name": "Kubernetes Administration & Cloud-Native Security (CKA)", "category": "Cloud & DevOps", "price": 6499, "instructor": "David Kowalski", "image_url": "https://images.unsplash.com/photo-1667372335854-c072b9886361?auto=format&fit=crop&w=600&q=80"},
        {"id": 301, "name": "Generative AI & LLM Agent Architecture with Python", "category": "AI & Data Engineering", "price": 7499, "instructor": "Priya Sharma", "image_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=600&q=80"},
        {"id": 103, "name": "Modern Microservices with Go & gRPC Systems", "category": "Software Engineering", "price": 5499, "instructor": "David Kowalski", "image_url": "https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=600&q=80"},
        {"id": 202, "name": "AWS Solutions Architect Professional Bootcamp", "category": "Cloud & DevOps", "price": 6999, "instructor": "Marcus Vance", "image_url": "https://images.unsplash.com/photo-1607799279861-4dd421887fb3?auto=format&fit=crop&w=600&q=80"},
        {"id": 302, "name": "Retrieval-Augmented Generation (RAG) & Vector DBs", "category": "AI & Data Engineering", "price": 6999, "instructor": "Priya Sharma", "image_url": "https://images.unsplash.com/photo-1677442136019-21780efad99a?auto=format&fit=crop&w=600&q=80"},
    ]

    fallback_home_imgs = [
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1618401471353-b98aedd04e11?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1507238691740-187a5b1d37b8?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=600&q=80"
    ]

    for idx, dbc in enumerate(db_courses):
        if not getattr(dbc, 'image', None):
            dbc.image_url = fallback_home_imgs[idx % len(fallback_home_imgs)]
        else:
            try:
                dbc.image_url = dbc.image.url
            except Exception:
                dbc.image_url = str(dbc.image)

    display_courses = (db_courses + featured_6)[:6]

    try:
        recent_achievements = Certificate.objects.select_related('user', 'course').order_by('-issued_at')[:5]
    except Exception:
        recent_achievements = []

    context = {
        'courses': display_courses,
        'recent_achievements': recent_achievements,
        'total_courses': len(display_courses),
    }
    return render(request, 'home.html', context)

    

User = get_user_model()

# Helpers
# --- 1. Security & Session Helpers ---
def is_superuser(user):
    # Verifies if the User Node has administrative clearance.
    return user.is_authenticated and user.is_superuser

def ensure_session_key(request):
    # Guarantees a unique session handshake is established.
    # Critical for pre-authentication tracking and analytics signals.
    
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key

# --- 2. Password Recovery Node ---
def forgot_password(request):
    # Security Recovery Handshake.
    # Initializes the identity verification process for lost credentials.

    if request.method == "POST":
        email = request.POST.get("email")
        # Here you would trigger the password reset email logic
        # messages.success(request, f"Recovery packet dispatched to {email}")
        return redirect("login")
        
    return render(request, "forgot_password.html")
    
# ------------------------------- STATIC PAGES -------------------------------

# --- 1. Brand Identity Nodes ---
def about_page(request):
    # Provides high-fidelity brand story and platform statistics.
    stats = {
        "active_students": "12K+",
        "expert_mentors": "45+",
        "success_rate": "94%"
    }
    return render(request, "about.html", {"stats": stats})

def trainers_page(request):
    # Fetches all verified instructor nodes with their curriculum counts.
    # Annotate can be used here to count courses per trainer
    trainers = InstructorProfile.objects.select_related('user').all()
    return render(request, "trainers.html", {"trainers": trainers})

def contact_page(request):
    # Deployment node for user inquiries and support handshakes.
    return render(request, "contact.html")

# --- 2. Identity & Security Audit Nodes ---
@login_required
def profile_page(request):
    user = request.user
    enrollments = list(MyCourse.objects.filter(user=user).select_related('course'))
    
    total_completed_lessons = LessonComplete.objects.filter(user=user).count()
    avatar_url = f"https://ui-avatars.com/api/?name={user.first_name or user.username}&background=4f46e5&color=fff"

    context = {
        "user": user,
        "user_avatar_url": avatar_url,
        "courses": enrollments,
        "total_courses": len(enrollments),
        "total_lessons": total_completed_lessons,
        "node_status": "AUTHENTICATED_SECURE"
    }
    return render(request, "profile.html", context)

@login_required
def profile_history(request):
    # Security Audit Node:
    # Tracks all historical access packets and active session handshakes.
    # Optimized lookup for security logs
    logins = LoginActivity.objects.filter(user=request.user).order_by("-login_time")[:20]
    sessions = UserSession.objects.filter(user=request.user).order_by("-login_time")

    return render(request, "profile_history.html", {
        "logins": logins,
        "sessions": sessions,
        "current_session_key": getattr(request.session, "session_key", ""),
        "audit_timestamp": timezone.now()
    })
    
# --- 3. Events & Workshop Deployment ---
def events_list(request):
    # Displays all upcoming technical workshops and live sync events."""
    events = Event.objects.filter(is_active=True).order_by("start_date")
    return render(request, "events.html", {"events": events})

def event_detail(request, slug):
    # Detailed provisioning for a specific workshop event."""
    event = get_object_or_404(Event, slug=slug)
    # Check if user is already registered if applicable
    return render(request, "event_detail.html", {"event": event})


@login_required
def notifications_view(request):
    return render(request, 'notifications.html')


#-------------------------------------Main Login START------------------------------------

#-------------------------------------Main Email OTP Auth START------------------------------------

def send_otp(request):
    if request.method == "POST":
        import json, random
        from datetime import timedelta
        from django.core.mail import send_mail
        from django.conf import settings
        from .models import EmailOTP

        if request.content_type == "application/json":
            try:
                data = json.loads(request.body)
                email = data.get("email", "").strip().lower()
            except Exception:
                email = ""
        else:
            email = request.POST.get("email", "").strip().lower()

        if not email or "@" not in email:
            return JsonResponse({"success": False, "message": "Please enter a valid real email address."})

        # Generate 4-digit numeric OTP code
        otp_code = f"{random.randint(1000, 9999)}"
        expires_at = timezone.now() + timedelta(minutes=2)

        # Invalidate existing pending OTPs for this email
        EmailOTP.objects.filter(email=email, is_verified=False).update(is_verified=True)

        # Save new 4-digit OTP record
        EmailOTP.objects.create(
            email=email,
            otp_code=otp_code,
            expires_at=expires_at
        )

        request.session['pending_otp_email'] = email

        # Send Real Email via SMTP using Modern HTML Card Template
        try:
            from django.core.mail import EmailMultiAlternatives
            from django.template.loader import render_to_string

            subject = f"Mentor Login Code: {otp_code}"
            html_content = render_to_string("emails/login_otp.html", {"otp_code": otp_code, "email": email})
            text_content = f"Your 4-Digit Login Verification Code for Mentor is: {otp_code} (expires in 1 minute)."
            
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=False)

            return JsonResponse({
                "success": True, 
                "email": email, 
                "message": f"4-digit verification code sent to {email}."
            })
        except Exception as e:
            print(f"[SMTP SEND NOTICE] Email dispatch details for {email}: {e}")
            return JsonResponse({
                "success": True, 
                "email": email, 
                "message": f"Verification code generated for {email}."
            })

    return JsonResponse({"success": False, "message": "Invalid request method."})


def verify_otp(request):
    if request.method == "POST":
        import json
        from .models import EmailOTP
        from django.contrib.auth import get_user_model, login

        if request.content_type == "application/json":
            try:
                data = json.loads(request.body)
                email = data.get("email", "").strip().lower()
                otp_code = data.get("otp_code", "").strip()
            except Exception:
                email = ""
                otp_code = ""
        else:
            email = request.POST.get("email", "").strip().lower()
            otp_code = request.POST.get("otp_code", "").strip()

        if not email:
            email = request.session.get('pending_otp_email', '')

        if not email or not otp_code or len(otp_code) != 4:
            return JsonResponse({"success": False, "message": "Please enter a valid 4-digit code."})

        otp_record = EmailOTP.objects.filter(
            email=email,
            otp_code=otp_code,
            is_verified=False,
            expires_at__gte=timezone.now()
        ).order_by("-created_at").first()

        if not otp_record:
            return JsonResponse({"success": False, "message": "Invalid or expired 4-digit verification code."})

        # Mark OTP verified
        otp_record.is_verified = True
        otp_record.save()

        # Find or create User node
        User = get_user_model()
        user = User.objects.filter(email=email).first()

        if not user:
            import random
            base_username = email.split('@')[0].replace('.', '_')
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=base_username.capitalize(),
                is_staff=False,
                is_superuser=False
            )

        # Log in the user safely without triggering standard User model BigAutoField integer save
        try:
            from django.contrib.auth.signals import user_logged_in
            user_logged_in.disconnect(dispatch_uid='update_last_login')
        except Exception:
            pass

        login(request, user)
        request.session['access_level'] = 'standard_user'
        if 'pending_otp_email' in request.session:
            del request.session['pending_otp_email']

        messages.success(request, f"IDENTITY VERIFIED: Welcome back, {user.first_name or user.username}!")
        return JsonResponse({"success": True, "redirect_url": reverse("home"), "message": "Login successful!"})

    return JsonResponse({"success": False, "message": "Invalid request method."})


def google_login(request):
    if request.method == "POST":
        import json, random
        from django.contrib.auth import get_user_model, login

        try:
            data = json.loads(request.body)
            email = data.get("email", "").strip().lower()
            name = data.get("name", "")
        except Exception:
            email = request.POST.get("email", "").strip().lower()
            name = request.POST.get("name", "")

        if not email:
            return JsonResponse({"success": False, "message": "Google authentication failed."})

        User = get_user_model()
        user = User.objects.filter(email=email).first()

        if not user:
            base_username = email.split('@')[0].replace('.', '_')
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=name or base_username.capitalize(),
                is_staff=False,
                is_superuser=False
            )

        try:
            from django.contrib.auth.signals import user_logged_in
            user_logged_in.disconnect(dispatch_uid='update_last_login')
        except Exception:
            pass

        login(request, user)
        messages.success(request, f"GOOGLE AUTH VERIFIED: Welcome {user.first_name or user.username}!")
        return JsonResponse({"success": True, "redirect_url": reverse("home")})

    return JsonResponse({"success": False, "message": "Invalid request method."})


# PERMANENT ACCOUNT DELETION OTP HANDSHAKES
@login_required
def send_delete_otp(request):
    if request.method == "POST":
        import random
        from .models import EmailOTP
        
        user = request.user
        email = user.email
        if not email:
            return JsonResponse({"success": False, "message": "No email address associated with this account."})

        # Generate 4-digit numeric OTP
        otp_code = f"{random.randint(1000, 9999)}"
        expires_at = timezone.now() + timedelta(minutes=1)

        # Invalidate previous unverified OTPs for this email
        EmailOTP.objects.filter(email=email, is_verified=False).update(is_verified=True)

        # Save new deletion OTP record
        EmailOTP.objects.create(
            email=email,
            otp_code=otp_code,
            expires_at=expires_at
        )

        try:
            from django.core.mail import EmailMultiAlternatives
            from django.template.loader import render_to_string

            subject = f"Mentor Account Deletion Code: {otp_code}"
            html_content = render_to_string("emails/delete_otp.html", {
                "otp_code": otp_code,
                "user_name": user.first_name or user.username
            })
            text_content = f"Your 4-Digit Account Deletion Verification Code for Mentor is: {otp_code} (expires in 1 minute)."
            
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=False)

            return JsonResponse({
                "success": True, 
                "message": f"Security verification code sent to {email}."
            })
        except Exception as e:
            print(f"[DELETE OTP SEND ERROR] {email}: {e}")
            return JsonResponse({
                "success": True, 
                "message": f"Verification code generated for {email}."
            })

    return JsonResponse({"success": False, "message": "Invalid request method."})


@login_required
def verify_delete_otp(request):
    if request.method == "POST":
        import json
        from .models import EmailOTP, MyCourse, UserCourseMapping, LessonComplete
        from django.contrib.auth import logout

        user = request.user
        email = user.email

        if request.content_type == "application/json":
            try:
                data = json.loads(request.body)
                otp_code = data.get("otp_code", "").strip()
            except Exception:
                otp_code = ""
        else:
            otp_code = request.POST.get("otp_code", "").strip()

        if not otp_code or len(otp_code) != 4:
            return JsonResponse({"success": False, "message": "Please enter a valid 4-digit security code."})

        otp_record = EmailOTP.objects.filter(
            email=email,
            otp_code=otp_code,
            is_verified=False,
            expires_at__gte=timezone.now()
        ).order_by("-created_at").first()

        if not otp_record:
            return JsonResponse({"success": False, "message": "Invalid or expired verification code."})

        # Mark OTP as verified
        otp_record.is_verified = True
        otp_record.save()

        # Execute permanent data purge from MongoDB
        try:
            MyCourse.objects.filter(user=user).delete()
            UserCourseMapping.objects.filter(user=user).delete()
            LessonComplete.objects.filter(user=user).delete()
            EmailOTP.objects.filter(email=email).delete()
            
            # Delete user record itself
            user.delete()
        except Exception as e:
            print(f"[ACCOUNT DELETION PURGE NOTICE] Partial or direct delete on {email}: {e}")
            try:
                user.delete()
            except Exception:
                pass

        # Terminate session
        logout(request)
        messages.success(request, "ACCOUNT DELETED: Your account and associated data have been permanently removed.")
        return JsonResponse({"success": True, "redirect_url": reverse("home"), "message": "Account successfully deleted."})

    return JsonResponse({"success": False, "message": "Invalid request method."})



# REAL EMAIL OTP LOGIN VIEW
def login_form(request):
    if request.user.is_authenticated:
        return redirect("home")

    context = {
        "google_client_id": getattr(settings, 'NEXT_PUBLIC_GOOGLE_CLIENT_ID', ''),
    }
    return render(request, "login.html", context)


def signup(request):
    return redirect("login")




# LOGOUT VIEW
@login_required
@never_cache # Ensures the browser doesn't cache sensitive profile data after exit
def logout_page(request):
    
    # Decommissions the active session node and flushes security tokens.
    # 1. Capture user context for the final handshake message
    username = request.user.username.upper()
    
    # 2. Perform Global Logout
    # This flushes the session from the database and the client browser
    logout(request)
    
    # 3. Security Flash Message
    # Using technical branding to match your Figma design
    messages.info(request, f"NODE DISCONNECTED: Session for {username} terminated safely.")
    
    # 4. Redirect to Authentication Node
    return redirect("login")


# PROFILE (view/update)
@login_required
def profile_page(request):
    mycourses = MyCourse.objects.filter(user=request.user)
    total_courses = mycourses.count()
    total_lessons = sum(mc.lesson_count for mc in mycourses)
    return render(request, "profile.html", {
        "user": request.user,
        "courses": mycourses,
        "total_courses": total_courses,
        "total_lessons": total_lessons
    })

@login_required
def update_profile(request):
    if request.method == "POST":
        user = request.user
        user.first_name = request.POST.get("first_name", user.first_name)
        user.last_name = request.POST.get("last_name", user.last_name)
        user.email = request.POST.get("email", user.email)
        user.save()

        if request.FILES.get("profile_image"):
            from .models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.profile_image = request.FILES.get("profile_image")
            profile.save()

        messages.success(request, "Profile updated successfully!")
    return redirect("profile")


@login_required
def change_password(request):
    if request.method == "POST":
        user = request.user
        old = request.POST.get("old_password")
        new = request.POST.get("new_password")

        if user.check_password(old):
            user.set_password(new)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully!")
        else:
            messages.error(request, "Old password is incorrect!")

    return redirect("profile")


# COURSES
# def courses(request):
#     all_courses = Courses.objects.all()
#     return render(request, "courses.html", {"courses": all_courses})

def courses(request):
    query = request.GET.get('search', '').strip()
    category_param = request.GET.get('category', 'all').strip()
    
    db_courses = list(Courses.objects.all().order_by('-id'))
    
    # 60 Rich Pre-Populated Industry Engineering Courses Catalog with 60 Unique Cover Images
    catalog_60 = [
        # Software Engineering (20 Unique Tracks)
        {"id": 101, "name": "Full-Stack React & Node.js Architecture Masterclass", "category": "Software Engineering", "price": 4999, "instructor": "Alex Chen (Senior Staff Engineer)", "image": "https://images.unsplash.com/photo-1633356122544-f134324a6cee?auto=format&fit=crop&w=600&q=80"},
        {"id": 102, "name": "Advanced Python & Django REST Framework Protocols", "category": "Software Engineering", "price": 4499, "instructor": "Sarah Jenkins (Principal Lead)", "image": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=600&q=80"},
        {"id": 103, "name": "Modern Microservices with Go & gRPC Systems", "category": "Software Engineering", "price": 5499, "instructor": "David Kowalski (Go Core Contributor)", "image": "https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=600&q=80"},
        {"id": 104, "name": "Enterprise Java Spring Boot 3 & Microservices", "category": "Software Engineering", "price": 4999, "instructor": "Michael Zhang (Staff Architect)", "image": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=600&q=80"},
        {"id": 105, "name": "Full-Stack Next.js 14 App Router & TypeScript", "category": "Software Engineering", "price": 5299, "instructor": "Alex Chen (Senior Staff Engineer)", "image": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=600&q=80"},
        {"id": 106, "name": "Rust Systems Programming & Memory Safety Architecture", "category": "Software Engineering", "price": 5999, "instructor": "Elena Rostova (Systems Engineer)", "image": "https://images.unsplash.com/photo-1542831371-29b0f74f9713?auto=format&fit=crop&w=600&q=80"},
        {"id": 107, "name": "Frontend Engineering with Vue.js 3 & Pinia Architecture", "category": "Software Engineering", "price": 3999, "instructor": "Sarah Jenkins (Principal Lead)", "image": "https://images.unsplash.com/photo-1507238691740-187a5b1d37b8?auto=format&fit=crop&w=600&q=80"},
        {"id": 108, "name": "GraphQL API Design & Federated Schema Architecture", "category": "Software Engineering", "price": 4299, "instructor": "Michael Zhang (Staff Architect)", "image": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=600&q=80"},
        {"id": 109, "name": "TypeScript Deep Dive & Advanced Generic Patterns", "category": "Software Engineering", "price": 3499, "instructor": "Alex Chen (Senior Staff Engineer)", "image": "https://images.unsplash.com/photo-1516116211223-4258d6890654?auto=format&fit=crop&w=600&q=80"},
        {"id": 110, "name": "C++20 High Performance Computing & Memory Tuning", "category": "Software Engineering", "price": 5999, "instructor": "David Kowalski (Go Core Contributor)", "image": "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?auto=format&fit=crop&w=600&q=80"},
        {"id": 111, "name": "Building Scalable Real-time Apps with WebSockets & Redis", "category": "Software Engineering", "price": 4799, "instructor": "Michael Zhang (Staff Architect)", "image": "https://images.unsplash.com/photo-1551434678-e076c223a692?auto=format&fit=crop&w=600&q=80"},
        {"id": 112, "name": "Design Patterns & Object-Oriented Software Architecture", "category": "Software Engineering", "price": 4199, "instructor": "Sarah Jenkins (Principal Lead)", "image": "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?auto=format&fit=crop&w=600&q=80"},
        {"id": 113, "name": "Modern Angular 17 Enterprise Web Development", "category": "Software Engineering", "price": 4599, "instructor": "Alex Chen (Senior Staff Engineer)", "image": "https://images.unsplash.com/photo-1581291518633-83b4ebd1d83e?auto=format&fit=crop&w=600&q=80"},
        {"id": 114, "name": "iOS App Development with Swift 5 & SwiftUI 3D", "category": "Software Engineering", "price": 5199, "instructor": "Elena Rostova (Systems Engineer)", "image": "https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?auto=format&fit=crop&w=600&q=80"},
        {"id": 115, "name": "Android Kotlin Multiplatform & Clean Architecture", "category": "Software Engineering", "price": 5199, "instructor": "David Kowalski (Go Core Contributor)", "image": "https://images.unsplash.com/photo-1607252650355-f7fd0460ccdb?auto=format&fit=crop&w=600&q=80"},
        {"id": 116, "name": "Flutter 3 Cross-Platform Mobile Application Development", "category": "Software Engineering", "price": 4399, "instructor": "Sarah Jenkins (Principal Lead)", "image": "https://images.unsplash.com/photo-1551650975-87deedd944c3?auto=format&fit=crop&w=600&q=80"},
        {"id": 117, "name": "Progressive Web Apps (PWA) & Service Workers Mastery", "category": "Software Engineering", "price": 3299, "instructor": "Alex Chen (Senior Staff Engineer)", "image": "https://images.unsplash.com/photo-1504639725590-34d0984388bd?auto=format&fit=crop&w=600&q=80"},
        {"id": 118, "name": "WebAssembly (Wasm) & High Speed Browser Modules", "category": "Software Engineering", "price": 4899, "instructor": "Elena Rostova (Systems Engineer)", "image": "https://images.unsplash.com/photo-1531403009284-440f080d1e12?auto=format&fit=crop&w=600&q=80"},
        {"id": 119, "name": "Test-Driven Development (TDD) & Automated Testing Pipelines", "category": "Software Engineering", "price": 3799, "instructor": "Michael Zhang (Staff Architect)", "image": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=600&q=80"},
        {"id": 120, "name": "Domain-Driven Design (DDD) for Enterprise Systems", "category": "Software Engineering", "price": 5499, "instructor": "David Kowalski (Go Core Contributor)", "image": "https://images.unsplash.com/photo-1519389950473-47ba0277781c?auto=format&fit=crop&w=600&q=80"},

        # Cloud & DevOps (20 Unique Tracks)
        {"id": 201, "name": "Kubernetes Administration & Cloud-Native Security (CKA)", "category": "Cloud & DevOps", "price": 6499, "instructor": "David Kowalski (DevOps Architect)", "image": "https://images.unsplash.com/photo-1667372335854-c072b9886361?auto=format&fit=crop&w=600&q=80"},
        {"id": 202, "name": "AWS Solutions Architect Professional Bootcamp", "category": "Cloud & DevOps", "price": 6999, "instructor": "Marcus Vance (AWS Certified Staff)", "image": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=600&q=80"},
        {"id": 203, "name": "Terraform Infrastructure as Code (IaC) Masterclass", "category": "Cloud & DevOps", "price": 4999, "instructor": "David Kowalski (DevOps Architect)", "image": "https://images.unsplash.com/photo-1618401471353-b98aedd04e11?auto=format&fit=crop&w=600&q=80"},
        {"id": 204, "name": "Google Cloud Platform (GCP) Cloud Architect Certification", "category": "Cloud & DevOps", "price": 6499, "instructor": "Marcus Vance (AWS Certified Staff)", "image": "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?auto=format&fit=crop&w=600&q=80"},
        {"id": 205, "name": "Docker Containerization & Enterprise Registry Operations", "category": "Cloud & DevOps", "price": 3999, "instructor": "David Kowalski (DevOps Architect)", "image": "https://images.unsplash.com/photo-1605745341112-85968b19335b?auto=format&fit=crop&w=600&q=80"},
        {"id": 206, "name": "CI/CD Pipelines with GitHub Actions, ArgoCD & GitOps", "category": "Cloud & DevOps", "price": 5299, "instructor": "Marcus Vance (AWS Certified Staff)", "image": "https://images.unsplash.com/photo-1556075798-4825dfaaf498?auto=format&fit=crop&w=600&q=80"},
        {"id": 207, "name": "Microsoft Azure Solutions Architect Expert Certification", "category": "Cloud & DevOps", "price": 6499, "instructor": "David Kowalski (DevOps Architect)", "image": "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=600&q=80"},
        {"id": 208, "name": "Site Reliability Engineering (SRE) & Observability with Prometheus", "category": "Cloud & DevOps", "price": 5799, "instructor": "Marcus Vance (AWS Certified Staff)", "image": "https://images.unsplash.com/photo-1504868584819-f8e8b4b6d7e3?auto=format&fit=crop&w=600&q=80"},
        {"id": 209, "name": "Ansible Automation & Configuration Management at Scale", "category": "Cloud & DevOps", "price": 4299, "instructor": "David Kowalski (DevOps Architect)", "image": "https://images.unsplash.com/photo-1537432376769-00f5c2f4c8d2?auto=format&fit=crop&w=600&q=80"},
        {"id": 210, "name": "Cloud Security Zero-Trust & Identity IAM Protocols", "category": "Cloud & DevOps", "price": 5999, "instructor": "Marcus Vance (AWS Certified Staff)", "image": "https://images.unsplash.com/photo-1563986768609-322da13575f3?auto=format&fit=crop&w=600&q=80"},
        {"id": 211, "name": "Service Mesh Architecture with Istio & Envoy", "category": "Cloud & DevOps", "price": 5499, "instructor": "David Kowalski (DevOps Architect)", "image": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=600&q=80"},
        {"id": 212, "name": "Linux Kernel Administration & Shell Automation", "category": "Cloud & DevOps", "price": 3699, "instructor": "Marcus Vance (AWS Certified Staff)", "image": "https://images.unsplash.com/photo-1629654297299-c8506221ca97?auto=format&fit=crop&w=600&q=80"},
        {"id": 213, "name": "Serverless Architecture with AWS Lambda & DynamoDB", "category": "Cloud & DevOps", "price": 4799, "instructor": "David Kowalski (DevOps Architect)", "image": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=600&q=80"},
        {"id": 214, "name": "Multi-Cloud Infrastructure Design & Disaster Recovery", "category": "Cloud & DevOps", "price": 6899, "instructor": "Marcus Vance (AWS Certified Staff)", "image": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=600&q=80"},
        {"id": 215, "name": "Log Management & Monitoring with Elastic Stack (ELK)", "category": "Cloud & DevOps", "price": 4599, "instructor": "David Kowalski (DevOps Architect)", "image": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=600&q=80"},
        {"id": 216, "name": "HashiCorp Vault Secrets Management & Cryptography", "category": "Cloud & DevOps", "price": 5199, "instructor": "Marcus Vance (AWS Certified Staff)", "image": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=600&q=80"},
        {"id": 217, "name": "Network Engineering, BGP & Cloud VPC Peering", "category": "Cloud & DevOps", "price": 4899, "instructor": "David Kowalski (DevOps Architect)", "image": "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?auto=format&fit=crop&w=600&q=80"},
        {"id": 218, "name": "FinOps Cloud Cost Optimization & Billing Management", "category": "Cloud & DevOps", "price": 4199, "instructor": "Marcus Vance (AWS Certified Staff)", "image": "https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?auto=format&fit=crop&w=600&q=80"},
        {"id": 219, "name": "OpenTelemetry Distributed Tracing & APM Metrics", "category": "Cloud & DevOps", "price": 4999, "instructor": "David Kowalski (DevOps Architect)", "image": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=600&q=80"},
        {"id": 220, "name": "Chaos Engineering & System Resilience Testing with Litmus", "category": "Cloud & DevOps", "price": 5699, "instructor": "Marcus Vance (AWS Certified Staff)", "image": "https://images.unsplash.com/photo-1509228468518-180dd4864904?auto=format&fit=crop&w=600&q=80"},

        # AI & Data Engineering (20 Unique Tracks)
        {"id": 301, "name": "Generative AI & LLM Agent Architecture with Python", "category": "AI & Data Engineering", "price": 7499, "instructor": "Priya Sharma (AI Research Lead)", "image": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=600&q=80"},
        {"id": 302, "name": "Retrieval-Augmented Generation (RAG) & Vector DBs", "category": "AI & Data Engineering", "price": 6999, "instructor": "Priya Sharma (AI Research Lead)", "image": "https://images.unsplash.com/photo-1677442136019-21780efad99a?auto=format&fit=crop&w=600&q=80"},
        {"id": 303, "name": "PyTorch Deep Learning & Neural Network Architecture", "category": "AI & Data Engineering", "price": 6499, "instructor": "Dr. Aris Thorne (Chief AI Scientist)", "image": "https://images.unsplash.com/photo-1555255707-c07966088b7b?auto=format&fit=crop&w=600&q=80"},
        {"id": 304, "name": "Data Engineering Pipelines with Apache Spark & Snowflake", "category": "AI & Data Engineering", "price": 5999, "instructor": "Priya Sharma (AI Research Lead)", "image": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=600&q=80"},
        {"id": 305, "name": "MLOps Model Deployment & Pipeline Monitoring with MLflow", "category": "AI & Data Engineering", "price": 6299, "instructor": "Dr. Aris Thorne (Chief AI Scientist)", "image": "https://images.unsplash.com/photo-1504868584819-f8e8b4b6d7e3?auto=format&fit=crop&w=600&q=80"},
        {"id": 306, "name": "Natural Language Processing (NLP) with Transformers & HuggingFace", "category": "AI & Data Engineering", "price": 5799, "instructor": "Priya Sharma (AI Research Lead)", "image": "https://images.unsplash.com/photo-1655720828018-edd2daec9349?auto=format&fit=crop&w=600&q=80"},
        {"id": 307, "name": "Computer Vision & Autonomous Object Detection with YOLOv8", "category": "AI & Data Engineering", "price": 5999, "instructor": "Dr. Aris Thorne (Chief AI Scientist)", "image": "https://images.unsplash.com/photo-1507146426996-ef05306b995a?auto=format&fit=crop&w=600&q=80"},
        {"id": 308, "name": "Big Data Streaming Architecture with Apache Airflow & Kafka", "category": "AI & Data Engineering", "price": 5499, "instructor": "Priya Sharma (AI Research Lead)", "image": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=600&q=80"},
        {"id": 309, "name": "Fine-Tuning Open Source LLMs (Llama 3 & Mistral)", "category": "AI & Data Engineering", "price": 7299, "instructor": "Dr. Aris Thorne (Chief AI Scientist)", "image": "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?auto=format&fit=crop&w=600&q=80"},
        {"id": 310, "name": "PostgreSQL & NoSQL Database Optimization for High Throughput", "category": "AI & Data Engineering", "price": 4499, "instructor": "Priya Sharma (AI Research Lead)", "image": "https://images.unsplash.com/photo-1544383835-bda2bc66a55d?auto=format&fit=crop&w=600&q=80"},
        {"id": 311, "name": "Reinforcement Learning & Q-Learning Algorithmic Design", "category": "AI & Data Engineering", "price": 6899, "instructor": "Dr. Aris Thorne (Chief AI Scientist)", "image": "https://images.unsplash.com/photo-1509228468518-180dd4864904?auto=format&fit=crop&w=600&q=80"},
        {"id": 312, "name": "Data Warehousing & Dimensional Modeling with dbt", "category": "AI & Data Engineering", "price": 4999, "instructor": "Priya Sharma (AI Research Lead)", "image": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=600&q=80"},
        {"id": 313, "name": "LangChain & LlamaIndex Agent Framework Development", "category": "AI & Data Engineering", "price": 6599, "instructor": "Dr. Aris Thorne (Chief AI Scientist)", "image": "https://images.unsplash.com/photo-1531746790731-6c087fecd65a?auto=format&fit=crop&w=600&q=80"},
        {"id": 314, "name": "Feature Store Architecture & Real-Time Feature Engineering", "category": "AI & Data Engineering", "price": 5399, "instructor": "Priya Sharma (AI Research Lead)", "image": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=600&q=80"},
        {"id": 315, "name": "Time-Series Forecasting & Anomaly Detection Algorithms", "category": "AI & Data Engineering", "price": 4799, "instructor": "Dr. Aris Thorne (Chief AI Scientist)", "image": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=600&q=80"},
        {"id": 316, "name": "Speech Recognition & Audio Processing with Whisper API", "category": "AI & Data Engineering", "price": 5199, "instructor": "Priya Sharma (AI Research Lead)", "image": "https://images.unsplash.com/photo-1590602847861-f357a9332bbc?auto=format&fit=crop&w=600&q=80"},
        {"id": 317, "name": "Graph Neural Networks & Knowledge Graph Embeddings", "category": "AI & Data Engineering", "price": 6699, "instructor": "Dr. Aris Thorne (Chief AI Scientist)", "image": "https://images.unsplash.com/photo-1507238691740-187a5b1d37b8?auto=format&fit=crop&w=600&q=80"},
        {"id": 318, "name": "Data Governance, Quality Audit & Anonymization Protocols", "category": "AI & Data Engineering", "price": 4299, "instructor": "Priya Sharma (AI Research Lead)", "image": "https://images.unsplash.com/photo-1563986768609-322da13575f3?auto=format&fit=crop&w=600&q=80"},
        {"id": 319, "name": "Prompt Engineering & Advanced Context Window Management", "category": "AI & Data Engineering", "price": 3899, "instructor": "Dr. Aris Thorne (Chief AI Scientist)", "image": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=600&q=80"},
        {"id": 320, "name": "Multimodal AI Models (Vision & Audio) Integration", "category": "AI & Data Engineering", "price": 7199, "instructor": "Priya Sharma (AI Research Lead)", "image": "https://images.unsplash.com/photo-1677442136019-21780efad99a?auto=format&fit=crop&w=600&q=80"}
    ]

    # Curated fallback tech images for database courses
    fallback_images = [
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1618401471353-b98aedd04e11?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1667372335854-c072b9886361?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1677442136019-21780efad99a?auto=format&fit=crop&w=600&q=80"
    ]

    for idx, dbc in enumerate(db_courses):
        cat = getattr(dbc, 'category', '')
        if not cat or cat.lower() in ['uncategorized', 'general', 'batch']:
            dbc.category = "Software Engineering"
        
        # Attach image_url to model instance if image is empty
        if not dbc.image:
            dbc.image_url = fallback_images[idx % len(fallback_images)]
        else:
            try:
                dbc.image_url = dbc.image.url
            except Exception:
                dbc.image_url = str(dbc.image)

    all_courses = db_courses + catalog_60

    def get_course_attr(c, attr, default=""):
        if isinstance(c, dict):
            val = c.get(attr, default)
        else:
            val = getattr(c, attr, default)
        return str(val) if val is not None else default

    if query:
        q_lower = query.lower()
        all_courses = [
            c for c in all_courses 
            if q_lower in get_course_attr(c, 'name').lower()
            or q_lower in get_course_attr(c, 'category').lower()
        ]

    if category_param and category_param.lower() != 'all':
        import re
        def normalize_cat(s):
            return re.sub(r'[^a-z0-9]', '', str(s).lower())

        target_norm = normalize_cat(category_param)
        
        slug_aliases = {
            "softwareengineering": ["softwareengineering", "software"],
            "clouddevops": ["clouddevops", "cloud", "devops"],
            "dataai": ["aidataengineering", "dataai", "aidata", "dataengineering", "ai"],
        }
        allowed_norms = slug_aliases.get(target_norm, [target_norm])

        filtered = []
        for c in all_courses:
            cat_val = get_course_attr(c, 'category')
            cat_norm = normalize_cat(cat_val)

            if cat_norm in allowed_norms or target_norm in cat_norm or cat_norm in target_norm:
                filtered.append(c)
        all_courses = filtered

    context = {
        "courses": all_courses,
        "search_query": query,
        "active_category": category_param,
        "total_results": len(all_courses),
    }

    return render(request, "courses.html", context)


# MY COURSES / PRICING
from django.db.models import Count, Q, FloatField, ExpressionWrapper, F
@login_required
def our_courses(request, uid):
    # 1. Security Handshake: Prevent Cross-User Snooping
    if request.user.id != int(uid):
        return redirect("my_courses", uid=request.user.id)

    # 2. Optimized Query with Data Annotation
    # We fetch courses and calculate completion percentage directly in SQL for speed
    my_courses_raw = MyCourse.objects.filter(user=request.user).select_related('course')
    
    dashboard_data = []
    for entry in my_courses_raw:
        course = entry.course
        
        # Calculate Progress Metrics
        total_lessons = Lesson.objects.filter(course=course).count()
        completed_count = LessonComplete.objects.filter(
            user=request.user, 
            lesson__course=course
        ).count()
        
        # Math for Figma Progress Bars
        progress = int((completed_count / total_lessons) * 100) if total_lessons > 0 else 0
        
        dashboard_data.append({
            "instance": entry,
            "course": course,
            "progress": progress,
            "completed_count": completed_count,
            "total_count": total_lessons,
            "is_complete": progress == 100
        })

    # 3. Context Deployment
    context = {
        "dashboard_items": dashboard_data,
        "total_active_tracks": len(dashboard_data),
        "user_node": request.user.username.upper()
    }
    
    return render(request, "my_courses.html", context)


# COURSE DETAIL
@login_required
def course_detail(request, cid):
    course = None
    try:
        if str(cid).isdigit():
            course = Courses.objects.filter(id=int(cid)).first()
        else:
            course = Courses.objects.filter(id=cid).first()
    except Exception:
        course = None

    if not course and ObjectId.is_valid(str(cid)):
        try:
            course = Courses.objects.filter(id=ObjectId(str(cid))).first()
        except Exception:
            course = None

    # Fallback to catalog item dict if numeric ID matching catalog_60
    if not course and str(cid).isdigit():
        cid_int = int(cid)
        catalog_60_items = [
            {"id": 101, "name": "Full-Stack React & Node.js Architecture Masterclass", "category": "Software Engineering", "price": 4999, "instructor": "Alex Chen", "image": "https://images.unsplash.com/photo-1633356122544-f134324a6cee?auto=format&fit=crop&w=600&q=80"},
            {"id": 102, "name": "Advanced Python & Django REST Framework Protocols", "category": "Software Engineering", "price": 4499, "instructor": "Sarah Jenkins", "image": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=600&q=80"},
            {"id": 103, "name": "Modern Microservices with Go & gRPC Systems", "category": "Software Engineering", "price": 5499, "instructor": "David Kowalski", "image": "https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=600&q=80"},
            {"id": 201, "name": "Kubernetes Administration & Cloud-Native Security (CKA)", "category": "Cloud & DevOps", "price": 6499, "instructor": "David Kowalski", "image": "https://images.unsplash.com/photo-1667372335854-c072b9886361?auto=format&fit=crop&w=600&q=80"},
            {"id": 202, "name": "AWS Solutions Architect Professional Bootcamp", "category": "Cloud & DevOps", "price": 6999, "instructor": "Marcus Vance", "image": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=600&q=80"},
            {"id": 301, "name": "Generative AI & LLM Agent Architecture with Python", "category": "AI & Data Engineering", "price": 7499, "instructor": "Priya Sharma", "image": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=600&q=80"},
            {"id": 302, "name": "Retrieval-Augmented Generation (RAG) & Vector DBs", "category": "AI & Data Engineering", "price": 6999, "instructor": "Priya Sharma", "image": "https://images.unsplash.com/photo-1677442136019-21780efad99a?auto=format&fit=crop&w=600&q=80"}
        ]
        match_dict = next((item for item in catalog_60_items if item["id"] == cid_int), None)
        if match_dict:
            course, _ = Courses.objects.get_or_create(
                name=match_dict["name"],
                defaults={
                    "category": match_dict["category"],
                    "price": match_dict["price"],
                    "description": f"Master {match_dict['name']} with hands-on labs and senior mentorship."
                }
            )

    if not course:
        first_course = Courses.objects.first()
        if first_course and str(first_course.id) != str(cid):
            return redirect("course_detail", cid=str(first_course.id))
        messages.warning(request, "No active course tracks available.")
        return redirect("courses")

    # Auto-synchronize enrollment
    mycourse, _ = MyCourse.objects.get_or_create(user=request.user, course=course)
    UserCourseMapping.objects.get_or_create(user=request.user, course=course)

    # Fetch lessons or auto-generate default introductory lesson
    lessons = list(Lesson.objects.filter(course=course).order_by("order"))
    if not lessons:
        default_lesson = Lesson.objects.create(
            course=course,
            title=f"Introduction to {course.name}",
            description=f"Welcome to {course.name}. Work through each module to build practical skills.",
            order=1
        )
        lessons = [default_lesson]

    # Identify current active lesson
    lesson_id = request.GET.get("lesson")
    current_lesson = None
    if lesson_id:
        current_lesson = Lesson.objects.filter(id=lesson_id, course=course).first()
    if not current_lesson:
        current_lesson = lessons[0]

    # Fetch completion status
    completed_lessons = list(LessonComplete.objects.filter(
        user=request.user, 
        lesson__course=course
    ).values_list('lesson_id', flat=True))
    completed_ids = set(completed_lessons)

    lesson_data = []
    can_access_next = True
    for lesson in lessons:
        is_completed = lesson.id in completed_ids
        is_locked = not can_access_next
        lesson_data.append({
            "lesson": lesson,
            "is_completed": is_completed,
            "is_locked": is_locked,
            "is_active": lesson.id == current_lesson.id
        })
        can_access_next = is_completed

    total_count = len(lessons)
    completed_count = len(completed_ids)
    progress_percent = int((completed_count / total_count) * 100) if total_count > 0 else 0

    mycourse.progress = progress_percent
    mycourse.save(update_fields=['progress'])
    UserCourseMapping.objects.filter(user=request.user, course=course).update(progress=progress_percent)

    return render(request, "course_detail.html", {
        "course": course,
        "current_lesson": current_lesson,
        "lesson_data": lesson_data,
        "mycourse": mycourse,
        "progress_percent": progress_percent,
        "completed_count": completed_count,
        "total_count": total_count,
        "is_unlocked": True,
        "is_completed": current_lesson.id in completed_ids if current_lesson else False,
    })


def mark_lesson_complete(request, course_id, lesson_id):
    user = request.user
    lesson = Lesson.objects.filter(id=lesson_id).first()
    course = Courses.objects.filter(id=course_id).first()

    if not lesson or not course:
        return JsonResponse({"status": "error", "message": "Lesson or course record not found."}, status=404)

    # 1. Record lesson completion
    LessonComplete.objects.get_or_create(user=user, lesson=lesson)

    # 2. Recalculate total completed lessons for this course
    total_lessons = Lesson.objects.filter(course=course).count()
    completed_count = LessonComplete.objects.filter(user=user, lesson__course=course).count()

    progress_percent = int((completed_count / total_lessons) * 100) if total_lessons > 0 else 100

    # 3. Automatically update MyCourse and UserCourseMapping models
    MyCourse.objects.filter(user=user, course=course).update(
        progress=progress_percent
    )
    UserCourseMapping.objects.filter(user=user, course=course).update(
        progress=progress_percent,
        is_completed=(progress_percent >= 100)
    )

    # 4. Automatically issue Certificate when 100% completed
    cert_created = False
    if progress_percent >= 100 or completed_count >= total_lessons:
        cert, cert_created = Certificate.objects.get_or_create(user=user, course=course)

    # 5. Return updated telemetry metrics
    total_user_completed = LessonComplete.objects.filter(user=user).count()

    return JsonResponse({
        "status": "success",
        "completed": True,
        "progress_percent": progress_percent,
        "completed_count": completed_count,
        "total_count": total_lessons,
        "total_user_lessons_completed": total_user_completed,
        "certificate_issued": cert_created
    })

@login_required
def buy_now(request, course_id, user_id):
    # Security handshake: Ensure the URL ID matches the actual logged-in user
    if request.user.id != int(user_id):
        return redirect('home')
    
    # Your purchase logic here...
    return redirect('course_detail', cid=course_id)


#--------------------------Download Certificate ------------------------------
import uuid
import qrcode
from io import BytesIO
from django.utils import timezone
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

@login_required
def download_certificate(request, course_id):
    try:
        cert = Certificate.objects.get(user=request.user, course_id=course_id)
    except Certificate.DoesNotExist:
        return HttpResponse("SYSTEM_ERROR: Certificate record not found.", status=404)

    # --- 1. UNIQUE CRYPTOGRAPHIC ID GENERATION ---
    unique_uuid = str(uuid.uuid4())
    short_id = unique_uuid[:12].upper()
    issue_date = getattr(cert, 'issued_at', timezone.now())
    
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="CERT_{short_id}.pdf"'
    
    pdf = canvas.Canvas(response, pagesize=landscape(A4))
    width, height = landscape(A4)

    # --- 2. BACKGROUND ARCHITECTURE ---
    pdf.setFillColorRGB(0.99, 0.99, 1.0)
    pdf.rect(0, 0, width, height, fill=1)
    
    # Watermark Handshake
    pdf.saveState()
    pdf.setFont("Helvetica-Bold", 70)
    pdf.setFillColorRGB(0.96, 0.96, 0.98)
    pdf.translate(width/2, height/2)
    pdf.rotate(30)
    pdf.drawCentredString(0, 0, "A U T H E N T I C   C R E D E N T I A L")
    pdf.restoreState()

    # --- 3. PREMIUM BORDERS ---
    pdf.setStrokeColorRGB(0.07, 0.16, 0.38) # Navy
    pdf.setLineWidth(18)
    pdf.rect(10, 10, width-20, height-20, stroke=1, fill=0)
    pdf.setStrokeColorRGB(0.38, 0.40, 0.94) # Indigo
    pdf.setLineWidth(2)
    pdf.rect(30, 30, width-60, height-60, stroke=1, fill=0)

    # --- 4. NEW: ACHIEVEMENT RIBBON SYMBOL (Top Right) ---
    # medal_x, medal_y = width - 100, height - 100
    # # Draw Ribbons
    # pdf.setFillColorRGB(0.6, 0.1, 0.1) # Dark Crimson Ribbon
    # pdf.polygon([medal_x-20, medal_y, medal_x-35, medal_y-70, medal_x-5, medal_y-70], fill=1, stroke=0)
    # pdf.polygon([medal_x+20, medal_y, medal_x+35, medal_y-70, medal_x+5, medal_y-70], fill=1, stroke=0)
    # # Draw Gold Medal
    # pdf.setFillColorRGB(0.85, 0.65, 0.13)
    # pdf.circle(medal_x, medal_y, 40, fill=1, stroke=1)
    # pdf.setFillColor(colors.white)
    # pdf.setFont("Helvetica-Bold", 8)
    # pdf.drawCentredString(medal_x, medal_y + 5, "OFFICIAL")
    # pdf.drawCentredString(medal_x, medal_y - 8, "ACHIEVEMENT")

    # --- 5. HEADER ---
    pdf.setFillColorRGB(0.07, 0.16, 0.38)
    pdf.setFont("Helvetica-Bold", 35)
    pdf.drawCentredString(width/2, height - 90, "CERTIFICATE OF ACHIEVEMENT")
    pdf.setFont("Courier-Bold", 12)
    pdf.setFillColor(colors.gray)
    pdf.drawCentredString(width/2, height - 110, f"CERTIFICATE No: {short_id}")

    # --- 6. RECIPIENT NODE ---
    pdf.setFillColorRGB(0.4, 0.4, 0.4)
    pdf.setFont("Helvetica", 18)
    pdf.drawCentredString(width/2, height - 180, "This high-honor is awarded to")
    pdf.setFillColorRGB(0.06, 0.46, 0.28) # Success Green
    pdf.setFont("Helvetica-Bold", 50)
    full_name = (request.user.get_full_name() or request.user.username).upper()
    pdf.drawCentredString(width/2, height - 240, full_name)

    # --- 7. COURSE DETAILS ---
    pdf.setFillColorRGB(0.3, 0.3, 0.3)
    pdf.setFont("Helvetica", 16)
    pdf.drawCentredString(width/2, height - 290, "for mastering the professional curriculum in")
    pdf.setFillColorRGB(0.07, 0.16, 0.38)
    pdf.setFont("Helvetica-Bold", 30)
    pdf.drawCentredString(width/2, height - 335, cert.course.name.upper())

    # --- 8. QR CODE & VERIFICATION ---
    verify_url = f"http://{request.get_host()}/verify/cert/{cert.id}/"
    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    pdf.drawImage(ImageReader(qr_buffer), (width/2) - 45, 120, width=90, height=90)

    # --- 9. DYNAMIC FOOTER ---
    pdf.setFillColorRGB(0.07, 0.16, 0.38)
    pdf.rect(30, 40, width-60, 35, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Courier-Bold", 9)
    node_id = request.get_host().upper()
    pdf.drawCentredString(width/2, 55, f"UUID: {unique_uuid} | NODE: {node_id} | AUTH: VERIFIED_ENCRYPTED")

    # --- 10. SIGNATURES ---
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(80, 130, "MRUNAL CHAUDHARI")
    pdf.line(80, 125, 230, 125)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(80, 110, "Chief Executive Officer,  Mentor")
    
    pdf.drawRightString(width - 80, 130, f"ISSUED: {issue_date.strftime('%B %d, %Y')}")
    pdf.line(width - 230, 125, width - 80, 125)
    pdf.drawRightString(width - 80, 110, "Official Authority Signature")

    pdf.showPage()
    pdf.save()
    return response



#------------verify_certificate-------------------------------------

# def verify_certificate(request, cert_id):
#     """
#     Public node for credential verification.
#     """
#     try:
#         # Search the registry by the primary ID (int)
#         certificate = Certificate.objects.select_related('user', 'course').get(id=cert_id)
        
#         # Determine authenticity based on system records
#         # If the record exists in the Certificate table, we assume completion
#         is_authentic = True 
        
#         context = {
#             "certificate": certificate,
#             "student_name": certificate.user.get_full_name() or certificate.user.username,
#             "course_name": certificate.course.name,
#             "issue_date": certificate.issued_at,
#             "is_authentic": is_authentic,
#             "serial_no": certificate.cert_id or f"MLMS-REGEN-{certificate.id}",
#             "system_hash": hash(certificate.id) # Symbolic security hash
#         }
#     except Certificate.DoesNotExist:
#         context = {"is_authentic": False}

#     return render(request, "classapp/verify_certificate.html", context)

import urllib.parse

def verify_certificate(request, cert_id):
    try:
        certificate = Certificate.objects.select_related('user', 'course').get(id=cert_id)
        is_authentic = True
        
        # --- NEW: LINKEDIN SHARE HANDSHAKE ---
        base_url = f"http://{request.get_host()}/verify/cert/{cert_id}/"
        params = {
            'url': base_url,
            'title': f"Certified in {certificate.course.name} | Mentor",
            'summary': f"I have successfully mastered the {certificate.course.name} professional track.",
            'source': 'Mentor'
        }
        linkedin_url = f"https://www.linkedin.com/shareArticle?mini=true&{urllib.parse.urlencode(params)}"
        
        context = {
            "certificate": certificate,
            "is_authentic": is_authentic,
            "linkedin_url": linkedin_url,
            "student_name": certificate.user.get_full_name() or certificate.user.username,
            "course_name": certificate.course.name,
            "issue_date": certificate.issued_at,
            "serial_no": certificate.cert_id,
        }
    except Certificate.DoesNotExist:
        context = {"is_authentic": False}

    return render(request, "classapp/verify_certificate.html", context)


# #---------------Remove-------------------
# REMOVE PURCHASED COURSE
@login_required
def remove_course(request, cid):
    # 1. Use get_object_or_404 for technical safety
    # This ensures we only delete the course if it actually belongs to THIS user
    user_course = MyCourse.objects.filter(user=request.user, course_id=cid)
    
    if user_course.exists():
        user_course.delete()
        messages.success(request, "Curriculum track decommissioned from your dashboard.")
    else:
        messages.error(request, "Access Error: Course node not found in your cluster.")

    # 2. Redirect using the dynamic user ID for your 'my_courses' path
    return redirect("my_courses", user_id=request.user.id)




# #---------------CART-------------------
# CART (DB-backed)
@login_required
def add_to_cart(request, cid):
    course = None
    try:
        course = Courses.objects.filter(id=cid).first()
    except Exception:
        course = None

    if not course:
        first_course = Courses.objects.first()
        if first_course:
            course = first_course
        else:
            messages.error(request, "Course not found.")
            return redirect("courses")

    try:
        CartItem.objects.get_or_create(user=request.user, course=course)
    except Exception:
        pass

    cart_count = CartItem.objects.filter(user=request.user).count()

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "status": "success",
            "msg": "Added to cart!",
            "cart_count": cart_count,
            "redirect": "/cart/"
        })

    messages.success(request, f"'{course.name}' added to your cart!")
    return redirect("cart")


@login_required
def remove_from_cart(request, cid):
    try:
        CartItem.objects.filter(user=request.user, course_id=cid).delete()
    except Exception:
        pass

    items = CartItem.objects.filter(user=request.user).select_related('course')
    cart_count = items.count()
    subtotal = sum(float(item.course.price) for item in items if hasattr(item, 'course') and item.course)
    gst_provision = round(subtotal * 0.18, 2)
    final_total = subtotal + gst_provision

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "status": "success",
            "message": "Item removed from cart",
            "cart_count": cart_count,
            "total": float(subtotal),
            "gst": float(gst_provision),
            "final_total": float(final_total)
        })

    messages.success(request, "Item removed from cart.")
    return redirect("cart")



#-------------------------cart----------------------------
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CartItem

@login_required
def cart(request):
    """
    DISPLAY ANALYTICAL BAG (CART)
    Calculates subtotal, GST, and final provisioning cost.
    """
    items = CartItem.objects.filter(user=request.user).select_related("course")
    
    # Calculate Base Node Price
    total = sum(item.course.price for item in items)
    
    # Technical Handshake Fees
    gst = round(total * 0.18, 2)
    platform_fee = 3.00 if items.exists() else 0.00
    
    # Final Aggregate
    final_total = round(total + gst + platform_fee, 2)

    context = {
        "items": items,
        "total": total,
        "gst": gst,
        "platform_fee": platform_fee,
        "final_total": final_total,
        "item_count": items.count(),
    }
    return render(request, "cart.html", context)


#---------------------checkout_page-----------------------------
@login_required
def checkout_page(request):
    """
    PRE-CHECKOUT PROVISIONING NODE
    Ensures the user has items before allowing the secure handshake.
    """
    items = CartItem.objects.filter(user=request.user).select_related("course")

    # Guard Clause: Prevent empty checkout access
    if not items.exists():
        messages.warning(request, "Handshake Aborted: Analytical Bag is empty.")
        return redirect("cart")

    # Recalculate for Security Consistency
    total = sum(i.course.price for i in items)
    gst = round(total * 0.18, 2)
    platform_fee = 3.00
    final_total = round(total + gst + platform_fee, 2)

    return render(request, "checkout.html", {
        "items": items,
        "total": total,
        "gst": gst,
        "platform_fee": platform_fee,
        "final_total": final_total,
        "item_count": items.count(),
    })


# --- INVOICE PDF GENERATOR & HTML EMAIL DISPATCH ---
def generate_invoice_pdf(order, invoice_number):
    from io import BytesIO
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Clean Light Header Banner (Soft Indigo #EEF2FF)
    p.setFillColor(colors.HexColor("#EEF2FF"))
    p.rect(0, height - 100, width, 100, stroke=0, fill=1)

    # Top accent line (Primary Indigo #4F46E5)
    p.setFillColor(colors.HexColor("#4F46E5"))
    p.rect(0, height - 5, width, 5, stroke=0, fill=1)

    # Brand Title & Subtitle
    p.setFillColor(colors.HexColor("#1E1B4B"))
    p.setFont("Helvetica-Bold", 24)
    p.drawString(40, height - 48, "MENTOR")
    p.setFont("Helvetica-Bold", 9)
    p.setFillColor(colors.HexColor("#4F46E5"))
    p.drawString(40, height - 65, "TAX INVOICE & RECEIPT")

    # Payment Status Badge
    p.setFillColor(colors.HexColor("#059669"))
    p.setFont("Helvetica-Bold", 11)
    p.drawRightString(width - 40, height - 55, "✓ PAYMENT SUCCESSFUL")

    # Order & Invoice Metadata
    y = height - 135
    p.setFillColor(colors.HexColor("#0F172A"))
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y, f"INVOICE NUMBER: {invoice_number}")
    paid_date = getattr(order, 'paid_at', None)
    date_str = paid_date.strftime("%d %b %Y, %I:%M %p") if paid_date else ""
    p.drawRightString(width - 40, y, f"DATE: {date_str}")

    y -= 20
    p.setFont("Helvetica", 10)
    p.setFillColor(colors.HexColor("#475569"))
    user_name = order.user.get_full_name() or order.user.username
    p.drawString(40, y, f"Billed To: {user_name} ({order.user.email})")
    p.drawRightString(width - 40, y, "Payment Method: Online Card / NetBanking")

    # Table Header Box (Light Slate #F1F5F9)
    y -= 40
    p.setFillColor(colors.HexColor("#F1F5F9"))
    p.rect(40, y - 8, width - 80, 26, stroke=1, fill=1)
    p.setStrokeColor(colors.HexColor("#E2E8F0"))

    p.setFillColor(colors.HexColor("#475569"))
    p.setFont("Helvetica-Bold", 9)
    p.drawString(50, y, "#")
    p.drawString(80, y, "COURSE TRACK")
    p.drawString(330, y, "CATEGORY")
    p.drawRightString(width - 50, y, "PRICE (INR)")

    # Table Rows
    y -= 28
    p.setFont("Helvetica", 9)

    subtotal = 0.0
    items = list(order.items.all())
    for idx, item in enumerate(items, 1):
        if idx % 2 == 0:
            p.setFillColor(colors.HexColor("#F8FAFC"))
            p.rect(40, y - 6, width - 80, 22, stroke=0, fill=1)

        p.setFillColor(colors.HexColor("#64748B"))
        p.setFont("Helvetica-Bold", 9)
        p.drawString(50, y, f"{idx:02d}")

        p.setFillColor(colors.HexColor("#0F172A"))
        p.setFont("Helvetica-Bold", 9)
        course_name = item.course.name
        if len(course_name) > 38:
            course_name = course_name[:35] + "..."
        p.drawString(80, y, course_name)

        p.setFillColor(colors.HexColor("#4F46E5"))
        p.setFont("Helvetica", 9)
        p.drawString(330, y, str(getattr(item.course, 'category', 'General')))

        p.setFillColor(colors.HexColor("#0F172A"))
        p.setFont("Helvetica-Bold", 9)
        price_val = float(item.price)
        p.drawRightString(width - 50, y, f"INR {price_val:.2f}")
        subtotal += price_val

        y -= 22
        p.setStrokeColor(colors.HexColor("#F1F5F9"))
        p.line(40, y + 15, width - 40, y + 15)

    # Totals Section
    y -= 15
    gst = round(subtotal * 0.18, 2)
    total = float(order.total)

    p.setFont("Helvetica", 10)
    p.setFillColor(colors.HexColor("#64748B"))
    p.drawRightString(width - 160, y, "Subtotal:")
    p.setFillColor(colors.HexColor("#0F172A"))
    p.drawRightString(width - 50, y, f"INR {subtotal:.2f}")

    y -= 20
    p.setFillColor(colors.HexColor("#64748B"))
    p.drawRightString(width - 160, y, "GST (18% included):")
    p.setFillColor(colors.HexColor("#0F172A"))
    p.drawRightString(width - 50, y, f"INR {gst:.2f}")

    y -= 25
    # Total Box Highlight
    p.setFillColor(colors.HexColor("#EEF2FF"))
    p.rect(width - 240, y - 8, 200, 30, stroke=1, fill=1)
    p.setStrokeColor(colors.HexColor("#C7D2FE"))

    p.setFillColor(colors.HexColor("#4F46E5"))
    p.setFont("Helvetica-Bold", 11)
    p.drawString(width - 230, y, "TOTAL PAID:")
    p.drawRightString(width - 50, y, f"INR {total:.2f}")

    # Footer
    p.setStrokeColor(colors.HexColor("#E2E8F0"))
    p.line(40, 60, width - 40, 60)
    p.setFont("Helvetica", 9)
    p.setFillColor(colors.HexColor("#94A3B8"))
    p.drawCentredString(width / 2, 42, "Thank you for learning with Mentor. Official computer-generated tax invoice.")
    p.drawCentredString(width / 2, 28, "Support: support@mentor.edu | Website: www.mentor.edu")

    p.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def send_checkout_invoice_email(order, invoice_number):
    try:
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string

        user = order.user
        items = list(order.items.all())
        subtotal = round(sum(float(i.price) for i in items), 2)
        gst = round(subtotal * 0.18, 2)

        # Generate PDF Invoice Bytes
        pdf_bytes = generate_invoice_pdf(order, invoice_number)
        pdf_filename = f"Invoice_{invoice_number}.pdf"

        # Render HTML Email Body
        html_content = render_to_string("emails/checkout_invoice.html", {
            "order": order,
            "user": user,
            "items": items,
            "subtotal": subtotal,
            "gst": gst,
            "invoice_number": invoice_number
        })

        subject = f"Mentor Enrollment Confirmation & Invoice #{invoice_number}"
        text_content = f"Thank you for enrolling! Invoice #{invoice_number} is attached."

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.attach(pdf_filename, pdf_bytes, "application/pdf")
        msg.send(fail_silently=False)
    except Exception as e:
        print(f"[INVOICE EMAIL ERROR] Could not dispatch invoice to {order.user.email}: {e}")


#------------PROCESS ORDER--------------------
@login_required
def checkout_process(request):
    if request.method != "POST":
        return JsonResponse({'success': False, 'message': 'Invalid Request Method'}, status=400)

    try:
        with transaction.atomic():
            items = list(CartItem.objects.filter(user=request.user).select_related("course"))

            if not items:
                return JsonResponse({'success': False, 'message': 'Cart is empty. Checkout aborted.'})

            total = sum(i.course.price for i in items)
            gst = round(total * 0.18, 2)
            final_total = round(total + gst + 3.00, 2)

            order = Order.objects.create(
                user=request.user,
                total=final_total,
                status="PAID",
                paid_at=timezone.now()
            )

            for ci in items:
                OrderItem.objects.create(
                    order=order,
                    course=ci.course,
                    price=ci.course.price,
                    qty=1
                )

            # Safely clear cart items for MongoDB without select_related on delete query
            CartItem.objects.filter(user=request.user).delete()

        # Dispatch Modern HTML Invoice Email with PDF Attachment
        from django.utils.crypto import get_random_string
        inv_no = f"INV-{get_random_string(8).upper()}"
        send_checkout_invoice_email(order, inv_no)

        return JsonResponse({
            'success': True,
            'message': 'Payment Successful',
            'redirect_url': reverse('checkout_success')
        })
    except Exception as e:
        print(f"[CHECKOUT PROCESS ERROR] {e}")
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


#-----------Checkout Success-------------------------

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import  UserCourseMapping

@login_required
def checkout_success(request):
    try:
        # 1. Retrieve the most recent paid order node
        order = Order.objects.filter(user=request.user).latest("id")
    except Order.DoesNotExist:
        messages.error(request, "Provisioning record not found.")
        return redirect("checkout")

    # 2. Synchronize purchased courses to the permanent My Curriculum registry
    # We use transaction.atomic to ensure all mappings are created or none are
    with transaction.atomic():
        for item in order.items.all():
            # Create the permanent User <-> Course Handshake
            # get_or_create prevents duplicate nodes if the user refreshes the page
            UserCourseMapping.objects.get_or_create(
                user=request.user, 
                course=item.course,
                defaults={'progress': 0} # Initialize with 0 progress
            )

    # 3. Construct the technical breakdown for the success UI
    purchased_items = []
    for item in order.items.all():
        purchased_items.append({
            "name": item.course.name,
            "price": item.price,
            "image": item.course.image.url if item.course.image else "",
            "id": item.course.id,
            "category": getattr(item.course, 'category', 'General')
        })

    # 4. Finalize Session: Clear the deployment bag/cart
    if 'cart' in request.session:
        del request.session['cart']

    context = {
    "order": order,
    "order_id": order.id,
    "item_count": order.items.count(),
    "total": order.total,
    "purchased_items": purchased_items,
    # Safer Handshake: Check for common field names or use current time
    "timestamp": getattr(order, 'paid_at', getattr(order, 'created_at', timezone.now())) 
}

    return render(request, "checkout_success.html", context)



#---------------------------Health Check-------------------------
from django.http import HttpResponse
def health_check(request):
    # Standard technical handshake for liveness probes
    return HttpResponse("NODE_STATUS: OK", status=200)



#---------------------------Invoice-------------------------
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from django.utils import timezone
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

@login_required
def download_invoice(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except (Order.DoesNotExist, Exception):
        messages.error(request, "Invoice record not found.")
        return redirect("mycourses")

    invoice_number = f"INV-{str(order.id)[-8:].upper()}"
    pdf_bytes = generate_invoice_pdf(order, invoice_number)

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Invoice_{invoice_number}.pdf"'
    return response


#----------PAYMENT SUCCESS (legacy helper)----------------
@login_required
def payment_success(request):
    items = CartItem.objects.filter(user=request.user)
    for item in items:
        MyCourse.objects.get_or_create(user=request.user, course=item.course)
    items.delete()
    messages.success(request, "Payment successful! Courses unlocked.")
    return redirect("home")



#----------INSTRUCTOR  DASHBOARD-----------------------
# INSTRUCTOR DASHBOARD (non-admin)
@login_required
def instructor_dashboard(request):
    if not hasattr(request.user, "instructor_profile"):
        return render(request, "instructor/not_instructor.html")

    # If Courses model supports 'trainer' FK, use it; else return empty
    courses = Courses.objects.filter(trainer=request.user) if hasattr(Courses, "trainer") else Courses.objects.none()

    earnings_qs = OrderItem.objects.filter(order__status="PAID", course__in=courses)
    total_earnings = earnings_qs.aggregate(total=Sum("price"))["total"] or 0
    students_count = earnings_qs.values("order__user").distinct().count()

    top_courses = (earnings_qs
                .values("course__id", "course__name")
                .annotate(revenue=Sum("price"), sales=Count("id"))
                .order_by("-revenue")[:6])

    return render(request, "instructor/dashboard.html", {
        "courses": courses,
        "total_earnings": total_earnings,
        "students_count": students_count,
        "top_courses": top_courses
    })


#----------ADMIN DASHBOARD (staff only)------------------
@user_passes_test(lambda u: u.is_staff)
def admin_dashboard(request):
    total_courses = Courses.objects.count()
    total_students = Order.objects.values("user").distinct().count()
    total_earnings = Order.objects.filter(status="PAID").aggregate(Sum("total"))["total__sum"] or 0
    recent_orders = Order.objects.order_by("-created_at")[:8]
    top_courses = (OrderItem.objects
                .values("course__id", "course__name")
                .annotate(sales=Count("id"), revenue=Sum("price"))
                .order_by("-revenue")[:6])
    return render(request, "admin/dashboard_admin.html", {
        "total_courses": total_courses,
        "total_students": total_students,
        "total_earnings": total_earnings,
        "recent_orders": recent_orders,
        "top_courses": top_courses,
    })


#----------------Sales chart (served as PNG) - staff only-----------------------
@user_passes_test(lambda u: u.is_staff)
def admin_sales_chart(request):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from io import BytesIO
    from datetime import timedelta

    today = datetime.today()
    labels = []
    values = []
    for i in range(11, -1, -1):
        month = (today - timedelta(days=30 * i)).replace(day=1)
        start = month
        if month.month == 12:
            end = month.replace(year=month.year + 1, month=1)
        else:
            end = month.replace(month=month.month + 1)
        total = (Order.objects.filter(status="PAID", created_at__gte=start, created_at__lt=end).aggregate(Sum("total"))["total__sum"] or 0)
        labels.append(start.strftime("%b %y"))
        values.append(float(total))

    fig, ax = plt.subplots(figsize=(8, 3))
    ax.bar(labels, values)
    ax.set_title("Monthly Sales (last 12 months)")
    ax.set_ylabel("Earnings (INR)")
    ax.tick_params(axis='x', rotation=45)
    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type="image/png")


#-------------Invoice bulk download helper (admin action reuse)-----------------
def generate_invoice_pdf_bytes(invoice):
    buf = BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, height - 60, "MENTOR - INVOICE")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(40, height - 90, f"Invoice: {invoice.invoice_number}")
    pdf.drawString(40, height - 110, f"User: {invoice.order.user.username} ({invoice.order.user.email})")
    y = height - 150
    pdf.drawString(40, y, "Courses:")
    y -= 20
    for item in invoice.order.items.all():
        pdf.drawString(50, y, f"- {item.course.name}  ₹{item.price}")
        y -= 18
    y -= 10
    pdf.drawString(40, y, f"Total: ₹{invoice.order.total}")
    pdf.showPage()
    pdf.save()
    buf.seek(0)
    return buf.read()


#----------update process--------------------
@login_required
@require_POST
def update_progress(request, cid):
    course = get_object_or_404(Courses, id=cid)
    progress = int(request.POST.get("progress", 0))

    # limit 0–100
    progress = max(0, min(progress, 100))

    mycourse, created = MyCourse.objects.get_or_create(user=request.user, course=course)
    mycourse.progress = progress
    mycourse.save()

    # AJAX response
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "status": "ok",
            "progress": progress
        })

    messages.success(request, "Progress updated!")
    return redirect("course_detail", cid)


#-----Rating--------------------------------------
@login_required
@require_POST
def rate_course(request, cid):
    course = get_object_or_404(Courses, id=cid)
    rating = int(request.POST.get("rating", 0))

    # Clamp rating 1–5
    rating = max(1, min(rating, 5))

    # Store per-user rating
    cr, _ = CourseRating.objects.update_or_create(
        user=request.user,
        course=course,
        defaults={"rating": rating}
    )

    # Mirror rating inside MyCourse
    mycourse, _ = MyCourse.objects.get_or_create(user=request.user, course=course)
    mycourse.rating = rating
    mycourse.save()

    # AJAX support
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "status": "ok",
            "rating": rating,
            "avg_rating": course.avg_rating(),
        })

    messages.success(request, "Rating submitted!")
    return redirect("course_detail", cid)


#---------------------CONTACT-----------------------------
def contact_page(request):

    # Handles contact form:
    # - saves ContactMessage to DB
    # - sends email to SITE_ADMIN (settings.DEFAULT_FROM_EMAIL or CONTACT_EMAIL)
    # - supports AJAX (returns JSON) and normal POST (redirect + messages)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        subject = request.POST.get("subject", "").strip()
        message = request.POST.get("message", "").strip()

        # Basic validation
        if not name or not email or not message:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"ok": False, "error": "Please fill all required fields."}, status=400)
            messages.error(request, "Please fill all required fields.")
            return redirect("contact")

        # Save to DB
        cm = ContactMessage.objects.create(
            name=name, email=email, subject=subject, message=message
        )

        # Send email to site admin(s)
        subject_line = f"[Mentor Contact] {subject or 'No subject'} — {name}"
        body = (
            f"New contact message received:\n\n"
            f"Name: {name}\nEmail: {email}\nSubject: {subject}\n\nMessage:\n{message}\n\n"
            f"Message ID: {cm.id}"
        )
        recipients = [getattr(settings, "DEFAULT_FROM_EMAIL", None)]
        # fallback to a CONTACT_EMAIL if you set it
        contact_email = getattr(settings, "CONTACT_EMAIL", None)
        if contact_email:
            recipients = [contact_email]

        # remove possible None
        recipients = [r for r in recipients if r]

        email_sent = False
        if recipients:
            try:
                send_mail(subject_line, body, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)
                email_sent = True
            except BadHeaderError:
                # header injection or invalid header
                email_sent = False
            except Exception as e:
                # log in real app
                email_sent = False

        # Response path
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "ok": True,
                "msg": "Message sent. Thank you!",
                "email_sent": email_sent,
                "id": cm.id
            })

        # fallback standard POST
        messages.success(request, "Thanks — your message has been sent!")
        return redirect("contact")

    # GET
    return render(request, "contact.html")


#-----------------------GET IP----------------------------
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import time

# Global Rate Limiting Node
RATE_LIMIT = {}

def get_ip(request):
    x = request.META.get("HTTP_X_FORWARDED_FOR")
    return x.split(",")[0] if x else request.META.get("REMOTE_ADDR")

#-----------------------SUBSCRIBE EMAIL----------------------------
@csrf_exempt
def subscribe_ajax(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    ip = get_ip(request)
    now = time.time()

    # Rate-limit check (30s)
    if ip in RATE_LIMIT and now - RATE_LIMIT[ip] < 30:
        return JsonResponse({"status": "error", "message": "Slow down! Encryption tunnel busy."}, status=429)

    RATE_LIMIT[ip] = now
    form = SubscribeForm(request.POST)

    if form.is_valid():
        email = form.cleaned_data["email"]

        # DB Logic: Save only if not exists
        obj, created = SubscriberEmail.objects.get_or_create(
            email=email,
            defaults={
                "ip_address": ip,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")
            }
        )

        if not created:
            return JsonResponse({"status": "info", "message": "Node already provisioned for this email."})

        # Email Signal Transmission
        try:
            subject = "ACCESS GRANTED: Mentor Cluster"
            message = f"Provisioning successful for node: {email}\n\nWelcome to the Mentor ecosystem. Your subscription is now active on our technical cluster."
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
        except Exception as e:
            # We log the error but still return success because DB saved
            print(f"SMTP Error: {e}")

        return JsonResponse({
            "status": "success",
            "message": "Node Provisioned! Check your inbox.",
            "email_node": email
        })

    return JsonResponse({"status": "error", "message": "Invalid email protocol."}, status=400)


#-------------------------Instructor---------------------------------
@login_required
def request_instructor(request):
    # 1. Handshake: Retrieve existing request cluster for this user
    instructor_req = InstructorRequest.objects.filter(user=request.user).first()

    # 2. Protocol Check: If already approved, lock the gate
    if instructor_req and instructor_req.status == "APPROVED":
        messages.info(request, "IDENTITY_VERIFIED: You are already provisioned as an instructor.")
        return redirect("instructor_dashboard")

    if request.method == "POST":
        # 3. Data Extraction
        bio = request.POST.get("bio", "").strip()
        experience = request.POST.get("experience", "").strip()
        portfolio_url = request.POST.get("portfolio_url", "").strip()

        # 4. Input Validation Shield
        if not bio or not experience:
            messages.error(request, "VALIDATION_ERROR: Bio and Experience fields are required.")
            return render(request, "instructor/request_form.html", {"req": instructor_req})

        # 5. Database Sync (Create or Update)
        if not instructor_req:
            # First-time provision
            InstructorRequest.objects.create(
                user=request.user,
                bio=bio,
                experience=experience,
                portfolio_url=portfolio_url,
                status="PENDING"
            )
        else:
            # Update existing node (Useful if previously REJECTED)
            instructor_req.bio = bio
            instructor_req.experience = experience
            instructor_req.portfolio_url = portfolio_url
            instructor_req.status = "PENDING"  # Reset status for re-review
            instructor_req.save()

        messages.success(request, "HANDSHAKE_SUCCESS: Your instructor request is now in the review queue.")
        return redirect("profile")

    # 6. Render Form with existing data (to allow editing if status is not Approved)
    return render(request, "instructor/request_form.html", {"req": instructor_req})


#-------------------Instructor Dashboard------------------------------------
#from .models import InstructorRequest, Courses, Student  # Adjust based on your models
@login_required
def instructor_dashboard(request):
    # 1. Handshake: Check if the user has an instructor node provisioned
    instructor_req = InstructorRequest.objects.filter(user=request.user).first()

    # 2. Gatekeeper Logic: Block access if not fully APPROVED
    if not instructor_req or instructor_req.status != "APPROVED":
        return render(request, "instructor/not_approved.html", {
            "req": instructor_req,
            "status": instructor_req.status if instructor_req else "NO_REQUEST"
        })

    # 3. Dashboard Logic: Data Aggregation for Approved Instructors
    # Pulling real-time stats for the instructor's courses
    my_courses = Courses.objects.filter(instructor=request.user)
    total_students = Students.objects.filter(enrolled_courses__in=my_courses).distinct().count()
    
    context = {
        "instructor": instructor_req,
        "courses": my_courses,
        "student_count": total_students,
        "revenue": sum(c.price for c in my_courses), # Simplified example logic
    }

    return render(request, "instructor/dashboard.html", context)


#----------------------KYC UPLOADE----------------------
@login_required
def kyc_upload(request):
    
    # GET: show form + user's existing KYC docs
    # POST: accept upload (normal or AJAX)
    existing = KYCDocument.objects.filter(user=request.user).order_by("-submitted_at")
    if request.method == "POST":
        form = KYCDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            k = form.save(commit=False)
            k.user = request.user
            k.status = "PENDING"
            k.save()
            # optional: create thumbnail or call external OCR here
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "success": True,
                    "msg": "KYC submitted",
                    "id": k.id,
                    "status": k.status,
                })
            messages.success(request, "KYC submitted — admin will review it shortly.")
            return redirect("kyc_upload")
        else:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "errors": form.errors}, status=400)
    else:
        form = KYCDocumentForm()
    return render(request, "instructor/kyc_upload.html", {"form": form, "existing": existing})


@login_required
def kyc_detail(request, pk):
    doc = get_object_or_404(KYCDocument, pk=pk, user=request.user)
    return render(request, "instructor/kyc_detail.html", {"doc": doc})


#-------------------SEARCH URL-----------------------
from django.template.loader import render_to_string
from .models import Courses, SearchHistory

@require_GET
def search(request):
    query = request.GET.get("q", "").strip()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # 1. Database Provisioning: Save search intent
    if query:
        # Record search analytics (Save in DB)
        SearchHistory.objects.create(
            user=request.user if request.user.is_authenticated else None,
            query=query,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        # Query Set Handshake
        qs = Courses.objects.filter(
            models.Q(name__icontains=query) | 
            models.Q(description__icontains=query)
        ).distinct()
    else:
        qs = Courses.objects.none()

    # 2. Pagination Logic
    paginator = Paginator(qs, 12)
    page_number = request.GET.get("page", 1)
    results = paginator.get_page(page_number)

    # 3. AJAX Response Protocol
    if is_ajax:
        html = render_to_string("partials/search_results_grid.html", {"results": results})
        return JsonResponse({
            "status": "success",
            "html": html,
            "count": qs.count()
        })

    return render(request, "search_results.html", {"query": query, "results": results})


#------------------------Notification-------------------
from django.utils.timesince import timesince

@login_required
def notifications_view(request):

    # Standard view to render the full notification center page.
    # When user lands here, we can optionally mark all as read
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    
    all_notifications = Notification.objects.filter(user=request.user).order_at("-created_at")
    return render(request, "notifications/all_notifications.html", {
        "notifications": all_notifications
    })

@login_required
def notifications_api(request):
    
    # Optimized AJAX endpoint for the Navbar Bell.
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    recent = Notification.objects.filter(user=request.user).order_by("-created_at")[:6]
    
    items = []
    for n in recent:
        items.append({
            "id": n.id,
            "title": n.title,
            "message": n.message[:60] + "..." if len(n.message) > 60 else n.message,
            "url": n.url or "#",
            "is_read": n.is_read,
            "age": f"{timesince(n.created_at).split(',')[0]} ago"
        })
        
    return JsonResponse({
        "unread_count": unread_count, 
        "items": items,
        "all_notifications_url": "/notifications/"  # The landing page link
    })

#--------------------Notification mark read--------------------------
@login_required
@require_POST
def notifications_mark_read(request):
    # Mark a specific notification or ALL notifications as read.
    # Accepts JSON: {"id": <int>} or {"all": true}
    try:
        data = json.loads(request.body.decode("utf-8"))
        
        # Option A: Mark All as Read
        if data.get("all") is True:
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
            return JsonResponse({"ok": True, "message": "All marked as read"})

        # Option B: Mark Specific ID
        nid = data.get("id")
        if not nid:
            return JsonResponse({"error": "No ID provided"}, status=400)
            
        notif = get_object_or_404(Notification, id=int(nid), user=request.user)
        notif.is_read = True
        notif.save()
        return JsonResponse({"ok": True})

    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid payload format"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required
def notifications_all(request):

    # Full Notification Center with Pagination.
    qs = Notification.objects.filter(user=request.user).order_by("-created_at")
    paginator = Paginator(qs, 20) # Showing 20 per page for better performance
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, "notifications/notifications_all.html", {
        "notifications": page_obj,
        "unread_count": qs.filter(is_read=False).count()
    })


@require_POST
def acknowledge_notification(request):
    """
    Protocol: ACK_NODE_HANDSHAKE
    Marks a notification as read via AJAX.
    """
    import json
    try:
        data = json.loads(request.body)
        notification_id = data.get('id')
        
        # Security Handshake: Ensure notification belongs to the user
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        
        return JsonResponse({'success': True, 'status': 'NODE_ACKNOWLEDGED'})
    
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'NODE_NOT_FOUND'}, status=404)
    except Exception as e:
        # This prevents the 500 error by returning a controlled 400
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


#----------------MY COURSE---------------------------

def my_courses_redirect(request):

    # Architectural redirect node: Authenticated users are provisioned 
    # to their dashboard; others are routed to the login handshake.
    if request.user.is_authenticated:
        # Optimization: Use username or slug instead of raw ID for better security
        # Alternatively, if your 'my_courses' view uses request.user, 
        # you don't need to pass the ID at all.
        return redirect("my_courses") 

    # Protocol: Store the intended destination to improve UX flow
    messages.info(request, "AUTHENTICATION_REQUIRED: Please log in to access your curriculum node.")
    
    login_url = reverse("login")
    next_destination = reverse("my_courses")
    
    return redirect(f"{login_url}?next={next_destination}")


#------------------------MAIN EVENT START---------------------------------
# def events_list(request):
#     qs = Event.objects.filter(status="PUBLISHED", end__gte=timezone.now()).order_by("start")
#     # optional filters
#     cat = request.GET.get("category")
#     q = request.GET.get("q")
#     if cat:
#         qs = qs.filter(category__slug=cat)
#     if q:
#         qs = qs.filter(title__icontains=q)
#     return render(request, "events/events.html", {"events": qs})

def event_detail(request, slug):
    event = get_object_or_404(Event, slug=slug, status="PUBLISHED")
    # registrations (for user) & seat left
    is_registered = False
    if request.user.is_authenticated:
        is_registered = Registration.objects.filter(event=event, user=request.user, status__in=["PENDING","CONFIRMED"]).exists()
    return render(request, "events/event_detail.html", {"event": event, "is_registered": is_registered})

@require_POST
def register_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, status="PUBLISHED")
    # handle guest vs logged-in
    if request.user.is_authenticated:
        # create or return existing
        reg, created = Registration.objects.get_or_create(event=event, user=request.user,
                                                        defaults={"status":"PENDING"})
        name = request.user.get_full_name() or request.user.username
        email = request.user.email
    else:
        name = request.POST.get("name")
        email = request.POST.get("email")
        if not email or "@" not in email:
            return JsonResponse({"error":"Valid email required"}, status=400)
        reg, created = Registration.objects.get_or_create(event=event, guest_email=email,
                                                        defaults={"guest_name":name or email, "status":"PENDING"})
    # check capacity
    if event.capacity and event.seats_left == 0:
        # add to waitlist
        wl = WaitlistEntry.objects.create(event=event, name=name, email=email)
        # send ack email
        send_mail("Added to waitlist", f"You are on the waitlist for {event.title}", settings.DEFAULT_FROM_EMAIL, [email])
        return JsonResponse({"status":"waitlist"})
    # confirm right away (simple flow) — for real payments keep PENDING and confirm after payment
    reg.status="CONFIRMED"
    reg.confirmed_at=timezone.now()
    reg.save()

    # create certificate optionally later
    # send confirmation email with link to .ics and invoice etc.
    html = render_to_string("events/email_confirm.html", {"event": event, "name": name})
    send_mail(f"Registration Confirmed: {event.title}", html, settings.DEFAULT_FROM_EMAIL, [email], html_message=html)

    return JsonResponse({"status":"confirmed","registration_id": reg.id})

# Guest confirmation link (optional)
def confirm_guest_registration(request, code):
    reg = get_object_or_404(Registration, confirmation_code=code)
    reg.status="CONFIRMED"
    reg.confirmed_at = timezone.now()
    reg.save()
    return render(request, "events/confirmed.html", {"event": reg.event})

#----------------------Event list--------------------------------------
import uuid
from django.utils import timezone
from django.urls import reverse

def events_list(request):
    """
    Shows available tracks. Added 'is_live' logic to show students what's happening now.
    """
    now = timezone.now()
    qs = Event.objects.filter(status="PUBLISHED", end__gte=now).order_by("start")
    
    # Logic to identify currently active sessions
    for event in qs:
        event.is_active_now = event.start <= now <= event.end
        
    return render(request, "events/events.html", {"events": qs})

@require_POST
def register_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, status="PUBLISHED")
    user = request.user
    
    if not user.is_authenticated:
        return JsonResponse({"error": "AUTHENTICATION_REQUIRED"}, status=401)

    # 1. Handshake: Create Registration
    reg, created = Registration.objects.get_or_create(
        event=event, 
        user=user,
        defaults={"status": "CONFIRMED", "confirmed_at": timezone.now()}
    )

    # 2. Meeting Bridge Protocol: 
    # If a Google Meet link doesn't exist for this event, mentor generates/assigns one.
    # We ensure both Mentor and Student use the SAME link.
    meeting_url = event.meeting_link or f"https://meet.google.com/lookup/{uuid.uuid4().hex[:10]}"
    if not event.meeting_link:
        event.meeting_link = meeting_url
        event.save()

    # 3. Synchronized Notification Dispatch
    # Send same link to Student and Mentor
    context = {
        "event": event, 
        "name": user.get_full_name(),
        "meeting_url": meeting_url,
        "start_time": event.start.strftime("%Y-%m-%d %H:%M")
    }
    
    # Student Email
    html_student = render_to_string("events/email_confirm_student.html", context)
    send_mail(f"Session Bridge Active: {event.title}", html_student, settings.DEFAULT_FROM_EMAIL, [user.email], html_message=html_student)
    
    # Mentor Email (Handshake)
    html_mentor = render_to_string("events/email_confirm_mentor.html", context)
    send_mail(f"Student Joined Session: {event.title}", html_mentor, settings.DEFAULT_FROM_EMAIL, [event.mentor.email], html_message=html_mentor)

    return JsonResponse({
        "status": "confirmed",
        "meeting_bridge": meeting_url,
        "registration_id": reg.id
    })


#-----------ICS-------------------------------
# ICS generation
try:
    from icalendar import Calendar, Event as iEvent
except ImportError:
    Calendar, iEvent = None, None
import uuid

def event_ics(request, event_id):

    # Generates a high-fidelity .ics calendar invitation with 
    # synchronized meeting links and organization metadata.
    ev = get_object_or_404(Event, id=event_id)
    
    cal = Calendar()
    # Required for Outlook/Apple Calendar compatibility
    cal.add('prodid', '-//Mentor Cluster//mentor.com//')
    cal.add('version', '2.0')
    cal.add('method', 'REQUEST')

    ical = iEvent()
    
    # 1. Identity & Summary
    ical.add('summary', f"🚀 {ev.title}")
    ical.add('description', f"{ev.description}\n\nMentor: {ev.mentor.get_full_name()}\nJoin Session: {ev.meeting_link}")
    
    # 2. Synchronized Meeting Bridge
    # Setting the location as the Google Meet link makes it clickable in most UI apps
    ical.add('location', ev.meeting_link if ev.meeting_link else ev.location)
    
    # 3. Temporal Handshake (Timezone Aware)
    ical.add('dtstart', ev.start)
    ical.add('dtend', ev.end)
    ical.add('dtstamp', timezone.now())
    
    # 4. Unique Node Identifier (UID)
    # Essential so that if the event changes, the calendar recognizes it as an update
    ical.add('uid', f"EVENT-{ev.id}-{uuid.uuid4().hex[:8]}@mentor.com")
    
    # 5. Organizer Node
    ical.add('organizer', f"MAILTO:{settings.DEFAULT_FROM_EMAIL}")
    
    cal.add_component(ical)
    
    # Response Handshake
    response = HttpResponse(cal.to_ical(), content_type='text/calendar')
    # Clean filename using slug or title
    filename = f"Mentor-Session-{ev.id}.ics"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

#------------------create edit------------------
# Instructor-only create/edit
from django.utils.text import slugify
from django.contrib import messages
from .forms import EventCreationForm

def is_instructor(u):

    # High-fidelity permission check: Validates if user has an 
    # APPROVED instructor node or is a system administrator.
    if not u.is_authenticated: return False
    return u.is_staff or InstructorRequest.objects.filter(user=u, status="APPROVED").exists()


@user_passes_test(is_instructor, login_url='instructor_request')
def create_event(request):
    if request.method == "POST":
        # Pass request.user to the form's __init__
        form = EventCreationForm(request.POST, user=request.user)
        
        if form.is_valid():
            event = form.save(commit=False)
            event.mentor = request.user
            event.save()
            messages.success(request, "NODE_DEPLOYED: Your session is now synchronized with the cluster.")
            return redirect("instructor_dashboard")
    else:
        form = EventCreationForm(user=request.user)
        
    return render(request, "events/create_event.html", {"form": form})


#--------------Eevent Calneder----------------------------------
def events_calendar_json(request):
    qs = Event.objects.filter(status="PUBLISHED")
    items = []
    for e in qs:
        items.append({
            "id": e.id,
            "title": e.title,
            "start": e.start.isoformat(),
            "end": e.end.isoformat(),
            "url": reverse("event_detail", args=[e.slug])
        })
    return JsonResponse(items, safe=False)


def trainers(request):
    instructors = InstructorProfile.objects.select_related("user").all()
    return render(request, "trainers.html", {"instructors": instructors})


def instructor_detail(request, username):
    user = get_object_or_404(User, username=username)
    profile = getattr(user, "instructor_profile", None)
    if not profile:
        # optional: return 404 or show limited public page
        return render(request, "instructor/not_instructor.html", {"user_obj": user})

    # instructor stats
    top_courses = Courses.objects.filter(instructor=user).order_by("-id")[:6]
    reviews_qs = InstructorReview.objects.filter(instructor=user, approved=True).order_by("-created_at")
    paginator = Paginator(reviews_qs, 8)
    page = request.GET.get("page", 1)
    reviews = paginator.get_page(page)

    try:
        avg_rating = profile.avg_rating()
    except:
        avg_rating = 0

    context = {
        "user_obj": user,
        "profile": profile,
        "top_courses": top_courses,
        "reviews": reviews,
        "avg_rating": avg_rating,
        "review_form": InstructorReviewForm()
    }
    return render(request, "instructor/instructor_detail.html", context)


#-------------Instructor Review------------------------------
@login_required
@login_required
@require_POST
def instructor_review_create(request, username):
    """
    High-fidelity review node: Supports Upsert (Update or Insert) 
    via AJAX with real-time feedback.
    """
    instructor = get_object_or_404(User, username=username)
    
    # 1. Identity Guard: Ensure target is a provisioned instructor
    if not hasattr(instructor, "instructor_profile"):
        return JsonResponse({"error": "Target node is not a verified instructor."}, status=403)

    # 2. Protocol Guard: Prevent self-review loops
    if request.user == instructor:
        return JsonResponse({"error": "Self-review protocol is disabled."}, status=403)

    # 3. Upsert Logic: Check for existing review to update instead of erroring
    existing_review = InstructorReview.objects.filter(instructor=instructor, user=request.user).first()
    
    if existing_review:
        form = InstructorReviewForm(request.POST, instance=existing_review)
        action_type = "UPDATED"
    else:
        form = InstructorReviewForm(request.POST)
        action_type = "CREATED"

    if form.is_valid():
        # 4. Data Provisioning
        review = form.save(commit=False)
        review.instructor = instructor
        review.user = request.user
        review.approved = True # Defaulting to True, but can be set to False for moderation
        review.updated_at = timezone.now()
        review.save()

        # 5. Response Handshake: Return enriched data for UI updates
        return JsonResponse({
            "ok": True,
            "action": action_type,
            "data": {
                "id": review.id,
                "rating": review.rating,
                "title": review.title,
                "body": review.body,
                "author": request.user.get_full_name() or request.user.username,
                "timestamp": review.updated_at.strftime("%b %d, %Y"),
                "is_update": action_type == "UPDATED"
            },
            "message": f"Review successfully {action_type.lower()}."
        })
    
    # 6. Failure Protocol
    return JsonResponse({
        "error": "VALIDATION_FAILED", 
        "details": form.errors
    }, status=400)
    

#--------------AJAX ALL Courses-----------------------------
def ajax_all_courses(request):
    # High-fidelity AJAX node: Provisions the next set of courses 
    # using offset-based loading to prevent browser lag.
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return JsonResponse({"success": False, "error": "NODE_HANDSHAKE_FAILED"}, status=400)

    # 1. Offset Protocol: Get the current count of displayed courses from the request
    try:
        offset = int(request.GET.get('offset', 9))
        limit = int(request.GET.get('limit', 12)) # Load 12 more at a time
    except (ValueError, TypeError):
        offset = 9
        limit = 12

    # 2. Database Fetch: Slice the queryset based on the offset
    # Using [offset:offset+limit] prevents loading the entire DB into memory
    qs = Courses.objects.filter(status="PUBLISHED") # Only show active tracks
    courses = qs[offset : offset + limit]
    
    # 3. Capacity Check: Determine if more courses remain in the cluster
    has_next = qs.count() > (offset + limit)

    # 4. HTML Rendering Handshake
    html = render_to_string(
        "partials/course_card_col.html",
        {"courses": courses},
        request=request
    )

    return JsonResponse({
        "success": True,
        "html": html,
        "new_offset": offset + limit,
        "has_next": has_next
    })

#-------------------Mark Read Lession-----------------------------------
@login_required
def mark_lesson_complete(request, course_id, lesson_id):
    """
    High-fidelity progress handshake: Marks a lesson complete,
    recalculates course percentage, and provisions certificates.
    """
    user = request.user
    
    # 1. Lesson Verification Handshake
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = get_object_or_404(Courses, id=course_id)

    # 2. Database Sync: Mark completion node
    # get_or_create handles the "already completed" logic automatically
    completion_node, created = LessonComplete.objects.get_or_create(
        user=user,
        lesson=lesson
    )

    # 3. Aggregation Protocol: Calculating Progress Cluster
    total_lessons = Lesson.objects.filter(course=course).count()
    
    # Shield: Prevent ZeroDivisionError if course has no lessons provisioned
    if total_lessons == 0:
        return JsonResponse({"error": "No lessons provisioned for this course."}, status=400)

    completed_lessons_count = LessonComplete.objects.filter(
        user=user,
        lesson__course=course
    ).count()

    # Calculate percentage (clamped at 100)
    progress_percentage = min(int((completed_lessons_count / total_lessons) * 100), 100)

    # 4. State Persistence: Update MyCourse record
    mycourse, _ = MyCourse.objects.get_or_create(user=user, course=course)
    mycourse.progress = progress_percentage
    mycourse.save()

    # 5. Certificate Deployment Handshake
    cert_provisioned = False
    cert_url = ""
    
    if progress_percentage == 100:
        cert, cert_created = Certificate.objects.get_or_create(user=user, course=course)
        cert_provisioned = True
        # Assuming you have a get_absolute_url or similar in your Certificate model
        cert_url = cert.get_download_url() if hasattr(cert, 'get_download_url') else "#"

    # 6. Response Handshake
    return JsonResponse({
        "status": "success",
        "node_created": created,
        "metrics": {
            "completed": completed_lessons_count,
            "total": total_lessons,
            "progress_pct": progress_percentage
        },
        "provisioning": {
            "certificate_ready": cert_provisioned,
            "certificate_url": cert_url
        }
    })


#---------------MY COurses-------------------------------
@login_required
def my_courses(request):
    try:
        raw_courses = list(MyCourse.objects.filter(user=request.user).select_related('course'))
    except Exception:
        raw_courses = []

    my_courses_data = []
    fallback_imgs = [
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=600&q=80"
    ]

    for idx, entry in enumerate(raw_courses):
        course = entry.course
        if not course:
            continue

        total_lessons = Lesson.objects.filter(course=course).count()
        completed_count = LessonComplete.objects.filter(
            user=request.user,
            lesson__course=course
        ).count()

        calc_progress = int((completed_count / total_lessons) * 100) if total_lessons > 0 else entry.progress
        entry.progress = calc_progress
        entry.is_completed = calc_progress >= 100

        # Assign safe image URL
        if getattr(course, 'image_url', None):
            course_image = course.image_url
        elif getattr(course, 'image', None):
            try:
                course_image = course.image.url
            except Exception:
                course_image = str(course.image)
        else:
            course_image = fallback_imgs[idx % len(fallback_imgs)]
        
        course.display_image = course_image

        my_courses_data.append(entry)

    return render(request, "my_courses.html", {
        "courses": my_courses_data,
        "my_courses": my_courses_data,
        "enrolled_count": len(my_courses_data)
    })
    # 2. Sync Logic: Update the field only if it differs from the database count
    # This handles the "Update if not set" requirement efficiently
    

    # # 3. Provision context for the UI
    # context = {
    #     "courses": courses,
    #     "enrolled_count": courses.count(),
    #     "completed_count": courses.filter(progress=100).count()
    # }

    # return render(request, "my_courses.html", context)


@login_required
def remove_mycourse(request, pk):
    """
    Removes an enrolled course track from the user's curriculum.
    Deletes from BOTH MyCourse AND UserCourseMapping tables to guarantee permanent removal across Dashboard, Curriculum, and Hub.
    """
    deleted_any = False
    course_name = ""

    # 1. Delete from MyCourse table
    try:
        from django.db.models import Q
        mcs = MyCourse.objects.filter(user=request.user).filter(Q(id=pk) | Q(course_id=pk) | Q(course__id=pk))
        for mc in mcs:
            if mc.course:
                course_name = mc.course.name
            mc.delete()
            deleted_any = True
    except Exception:
        pass

    # 2. Delete from UserCourseMapping table
    try:
        from django.db.models import Q
        from .models import UserCourseMapping
        ucms = UserCourseMapping.objects.filter(user=request.user).filter(Q(id=pk) | Q(course_id=pk) | Q(course__id=pk))
        for ucm in ucms:
            if ucm.course and not course_name:
                course_name = ucm.course.name
            ucm.delete()
            deleted_any = True
    except Exception:
        pass

    if deleted_any:
        messages.success(request, f"Successfully removed '{course_name or 'Course Track'}' from your curriculum.")
    else:
        messages.info(request, "Course was already removed or not found in your curriculum.")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            "success": True,
            "message": "Course removed successfully.",
            "remaining_count": MyCourse.objects.filter(user=request.user).count()
        })

    next_url = request.META.get('HTTP_REFERER')
    if next_url and ('my-curriculum' in next_url or 'dashboard' in next_url or 'hub' in next_url):
        return redirect(next_url)
    return redirect("mycourses")


@login_required
def remove_from_dashboard(request, course_id):
    """
    Alias helper to remove course node from dashboard view.
    """
    return remove_mycourse(request, pk=course_id)


#---------------------------------------------------------------------
# Define your plans
PLANS = {
    'basic':  { 'name': 'Basic',   'price': 499 },
    'pro':    { 'name': 'Pro',     'price': 999 },
    'premium':{ 'name': 'Premium', 'price': 1999 },
}

def select_plan(request, plan_slug):
    plan = PLANS.get(plan_slug)
    if not plan:
        raise Http404("Plan not found")
    # Example: store selected plan in session or user cart
    request.session['selected_plan'] = plan_slug
    request.session['plan_price'] = plan['price']
    request.session['plan_name'] = plan['name']
    return redirect('checkout')



def checkout(request):
    """
    High-fidelity checkout node: Handles both initial page provisioning 
    and dynamic AJAX total recalculations.
    """
    plan_name = request.session.get('plan_name')
    price = request.session.get('plan_price')
    
    # 1. Integrity Guard
    if not plan_name or price is None:
        return redirect('home')

    # 2. Logic for AJAX Recalculation (e.g., Coupon Application)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        coupon_code = request.GET.get('coupon')
        discount = 0
        
        # Simple Coupon Handshake (Example)
        if coupon_code == "WELCOME10":
            discount = float(price) * 0.10
            
        new_total = float(price) - discount
        
        return JsonResponse({
            "success": True,
            "discount": discount,
            "new_total": new_total,
            "message": "Coupon applied successfully" if discount > 0 else "Invalid coupon"
        })

    # 3. Initial Provisioning
    context = {
        'plan_name': plan_name,
        'price': price,
        'courses': [{'name': plan_name, 'price': price}], 
        'total': price,
        'tax': float(price) * 0.05, # Example 5% tax provision
    }
    
    return render(request, 'checkout.html', context)



from django.db.models import Sum, Avg, Count
from django.utils import timezone
from .models import MyCourse, LessonComplete, Submission

@login_required
def command_center(request):
    user = request.user
    courses = MyCourse.objects.filter(user=user).select_related('course')
    
    # Feature 1: Dynamic XP Calculation (50xp per lesson, 200xp per lab)
    lessons_done = LessonComplete.objects.filter(user=user).count()
    labs_done = Submission.objects.filter(user=user, status="PASSED").count()
    total_xp = (lessons_done * 50)  + (labs_done * 200)
    
    # Feature 2: Real Avg. Completion
    avg_comp = courses.aggregate(Avg('progress'))['progress__avg'] or 0

    # Feature 3: Weekly Consistency Heatmap (Last 7 Days)
    today = timezone.now().date()
    heatmap = []
    for i in range(6, -1, -1):
        date = today - timezone.timedelta(days=i)
        active = LessonComplete.objects.filter(user=user, created_at__date=date).exists()
        heatmap.append({'day': date.strftime('%a'), 'state': 'active' if active else ''})

    return render(request, 'dashboard.html', {
        'courses': courses,
        'total_xp': f"{total_xp/1000:.1f}k" if total_xp > 1000 else total_xp,
        'xp_level': int(total_xp / 500) + 1,
        'avg_comp': int(avg_comp),
        'heatmap': heatmap,
        'recent_labs': Submission.objects.filter(user=user).order_by('-created_at')[:3]
    })


def is_mentor(user):
    return user.is_authenticated and (user.is_staff or hasattr(user, 'instructor_profile'))

@user_passes_test(is_mentor)
def mentor_review_list(request):
    """
    Mentor Control Room: Displays all pending lab nodes for evaluation.
    """
    pending_labs = Submission.objects.filter(status='PENDING').select_related('user', 'course').order_by('-created_at')
    return render(request, 'mentor/review_list.html', {'submissions': pending_labs})

@user_passes_test(is_mentor)
@require_POST
def update_submission_status(request, submission_id):
    """
    AJAX Endpoint: Updates lab status and synchronizes student XP.
    """
    import json
    data = json.loads(request.body)
    new_status = data.get('status') # 'PASSED' or 'FAILED'
    
    submission = get_object_or_404(Submission, id=submission_id)
    submission.status = new_status
    submission.save()

    return JsonResponse({
        "success": True, 
        "new_status": submission.get_status_display(),
        "student": submission.user.username
    })   
    
@login_required
def submit_lab(request, course_id=None):
    """
    Lab Submission Node: Provisioning student work to the 
    mentor review queue.
    """
    course = None
    if course_id:
        course = Courses.objects.filter(id=course_id).first()
        if not course and ObjectId.is_valid(course_id):
            course = Courses.objects.filter(id=ObjectId(course_id)).first()

    if not course:
        enrolled_mc = MyCourse.objects.filter(user=request.user).first()
        course = enrolled_mc.course if enrolled_mc else Courses.objects.first()

    if not course:
        messages.warning(request, "No active course tracks available.")
        return redirect("mycourses")

    # 1. Enrollment Guard: Ensure user has a MyCourse record
    is_enrolled = MyCourse.objects.filter(user=request.user, course=course).exists()
    if not is_enrolled:
        MyCourse.objects.get_or_create(user=request.user, course=course)
        UserCourseMapping.objects.get_or_create(user=request.user, course=course)

    if request.method == "POST":
        # 2. Data Extraction
        title = request.POST.get('lab_title') or request.POST.get('title') or f"Lab Project - {course.name}"
        link = request.POST.get('lab_link') or request.POST.get('link') or ""
        notes = request.POST.get('lab_content') or request.POST.get('content') or request.POST.get('notes') or ""
        content = f"Repository Link: {link}\n\nSubmission Notes:\n{notes}".strip() if link else notes
        
        # 3. Duplicate Prevention: Check if a pending submission already exists
        from .models import Submission
        active_submission = Submission.objects.filter(
            user=request.user, 
            course=course, 
            status='PENDING'
        ).exists()
        
        if active_submission:
            messages.warning(request, "You already have a pending review for this track.")
            return redirect('dashboard')

        # 4. Create Submission Node
        Submission.objects.create(
            user=request.user,
            course=course,
            title=title,
            content=content,
            status='PENDING'
        )

        messages.success(request, "Your lab is now in the Mentor Review Queue.")
        return redirect('dashboard')

    return render(request, 'submit_lab.html', {'course': course})


@login_required
def learning_hub(request):
    user = request.user
    # Fetch all enrolled courses
    enrolled = MyCourse.objects.filter(user=user)
    
    # Simple algorithm: Average progress per category
    # Example output: {'Backend': 88, 'Design': 45}
    skill_map = {}
    categories = enrolled.values_list('course__category__name', flat=True).distinct()
    
    for cat in categories:
        avg = enrolled.filter(course__category__name=cat).aggregate(Avg('progress'))['progress__avg']
        skill_map[cat] = int(avg) if avg else 0

    return render(request, 'hub.html', {'skill_map': skill_map})


def subscribe_node(request):
    if request.method == "POST":
        email = request.POST.get('email')
        if email:
            # Check if already exists to prevent duplicate handshake
            if not SubscriberEmail.objects.filter(email=email).exists():
                SubscriberEmail.objects.create(email=email)
                messages.success(request, "PROTOCOL_ACTIVE: Email synchronized with system feed.")
            else:
                messages.info(request, "NODE_EXISTS: This email is already in the buffer.")
        return redirect(request.META.get('HTTP_REFERER', 'hub'))
    return redirect('hub')



@login_required
def remove_from_dashboard(request, course_id):
    if request.method == "POST":
        # Find the enrollment record for the current user and the specific course
        enrollment = get_object_or_404(MyCourse, user=request.user, course_id=course_id)
        
        # Option A: Permanently delete the enrollment
        enrollment.delete()
        
        # Option B: Just hide it (if you have an 'is_active' field)
        # enrollment.is_active = False
        # enrollment.save()
        
    return redirect('profile') # Redirect back to the Student Hub/Profile



# def custom_404_view(request, exception):
#     return render(request, '404.html', status=404)
def custom_404_view(request, exception):
    """
    Protocol: 404_NODE_NOT_FOUND
    Triggered when a requested resource is outside the curriculum index.
    """
    return render(request, '404.html', {
        'error_code': '404',
        'status_message': 'RESOURCE_NOT_FOUND_IN_BUFFER'
    }, status=404)



def events_list(request):
    """
    High-fidelity event list: Filters for published, upcoming tracks 
    with real-time search and category handshakes.
    """
    now = timezone.now()
    
    # 1. Base Query: Only show PUBLISHED events that haven't ended yet
    # We order by 'start' so the next upcoming event is first
    qs = Event.objects.filter(
        status="PUBLISHED", 
        end__gte=now
    ).order_by('start')

    # 2. Search Handshake: Filter by title or description
    query = request.GET.get('q')
    if query:
        qs = qs.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query)
        )

    # 3. Category Protocol: Filter by category slug if provided
    category_slug = request.GET.get('category')
    if category_slug:
        qs = qs.filter(category__slug=category_slug)

    # 4. Meta-Logic: Tagging "Live Now" events for the UI
    for event in qs:
        event.is_live = event.start <= now <= event.end

    context = {
        "events": qs,
        "current_query": query,
        "current_category": category_slug,
        "total_count": qs.count()
    }

    return render(request, "events.html", context)



from django.http import JsonResponse
from django.db.models import Avg
from django.contrib.auth.decorators import login_required
from .models import UserCourseMapping

@login_required
def dashboard_telemetry_api(request):
    """
    Live Telemetry Node: 
    Provides real-time progress and metric data for the dashboard.
    """
    # 1. Fetch all active course nodes for the session user
    mappings = UserCourseMapping.objects.filter(user=request.user).select_related('course')
    
    # 2. Calculate Global Analytics
    avg_comp = mappings.aggregate(Avg('progress'))['progress__avg'] or 0
    
    # 3. Serialize Course Data for JS Consumption
    # We only send what is necessary to keep the payload lightweight
    courses_data = [
        {
            'id': m.id,
            'progress': m.progress,
            'is_completed': m.is_completed,
            'status': 'DEPLOYED' if m.is_completed else 'SYNCING'
        } 
        for m in mappings
    ]
        
    return JsonResponse({
        'avg_comp': round(avg_comp, 1),
        'active_count': mappings.count(),
        'courses': courses_data,
        'system_status': 'STABLE',
        'timestamp': timezone.now().isoformat()
    })


@login_required
def student_dashboard(request):
    """
    Main Student Dashboard
    """
    # 1. Fetch User Course Mappings & MyCourse Entries
    user_courses = list(UserCourseMapping.objects.filter(user=request.user).select_related('course'))
    existing_cids = {uc.course.id for uc in user_courses if uc.course}
    
    my_courses_list = MyCourse.objects.filter(user=request.user).select_related('course')
    for mc in my_courses_list:
        if mc.course and mc.course.id not in existing_cids:
            user_courses.append(mc)
            existing_cids.add(mc.course.id)
    
    # 2. Calculate Analytical Metrics
    total_progress = sum(getattr(uc, 'progress', 0) for uc in user_courses)
    avg_comp = (total_progress / len(user_courses)) if user_courses else 0
    
    # 3. Dynamic XP Logic
    completed_tracks = sum(1 for uc in user_courses if getattr(uc, 'progress', 0) >= 100)
    xp_points = (completed_tracks * 1000) + (int(avg_comp) * 10)
    
    # 4. Rank Logic
    if xp_points > 5000:
        rank, color = "Architect", "#A855F7"
    elif xp_points > 2000:
        rank, color = "Professional", "#6366F1"
    else:
        rank, color = "Scholar", "#10B981"

    # 5. Submission Telemetry
    recent_labs = Submission.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    heatmap = [{"day": d, "state": "active" if i % 2 == 0 else "inactive"} for i, d in enumerate(days)]

    context = {
        'courses': user_courses,
        'avg_comp': round(avg_comp, 1),
        'xp_level': rank,
        'xp_color': color,
        'total_xp': xp_points,
        'recent_labs': recent_labs,
        'heatmap': heatmap,
    }
    
    return render(request, 'dashboard.html', context)



@login_required
@never_cache
def profile_page(request):
    """
    Identity Hub: Central node for user data and curriculum stats.
    """
    mycourses = MyCourse.objects.filter(user=request.user).select_related('course')
    
    context = {
        "user": request.user,
        "courses": mycourses,
        "total_courses": mycourses.count(),
        "node_status": "AUTHENTICATED_SECURE",
        "rank": "ELITE" if mycourses.count() > 5 else "INITIATE"
    }
    return render(request, "profile.html", context)



@login_required
def update_profile_view(request):
    user = request.user
    
    if request.method == "POST":
        try:
            new_email = request.POST.get("email", "").strip().lower()
            first_name = request.POST.get("first_name", "").strip()
            last_name = request.POST.get("last_name", "").strip()
            
            if new_email and User.objects.exclude(pk=user.pk).filter(email=new_email).exists():
                messages.error(request, "This email address is already registered to another account.")
                return render(request, "update.html")

            user.first_name = first_name if first_name else user.first_name
            user.last_name = last_name if last_name else user.last_name
            if new_email:
                user.email = new_email
            user.save()
            
            if request.FILES.get("profile_image"):
                from .models import UserProfile
                profile, _ = UserProfile.objects.get_or_create(user=user)
                profile.profile_image = request.FILES.get("profile_image")
                profile.save()

            messages.success(request, "Your profile settings have been successfully updated!")
            return redirect('profile')
            
        except Exception as e:
            messages.error(request, f"Error updating profile: {str(e)}")
            return redirect('update_profile')

    return render(request, "update.html")


def custom_404_view(request, exception=None):
    return render(request, "404.html", status=404)


@login_required
def hub_page(request):
    """
    Student Learning Hub & Activity Hub
    """
    mycourses = list(MyCourse.objects.filter(user=request.user).select_related('course'))
    
    # Also include UserCourseMapping if not already present
    from .models import UserCourseMapping
    existing_course_ids = {mc.course.id for mc in mycourses if mc.course}
    mappings = UserCourseMapping.objects.filter(user=request.user).select_related('course')
    
    for m in mappings:
        if m.course and m.course.id not in existing_course_ids:
            mycourses.append(m)
            existing_course_ids.add(m.course.id)

    total_progress = sum(getattr(mc, 'progress', 0) for mc in mycourses)
    total_xp = max(total_progress * 10, 420)
    xp_level = (total_xp // 200) + 1
    
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    heatmap = [{"day": d, "state": "active" if i % 2 == 0 else "inactive"} for i, d in enumerate(days)]
    skill_map = {
        "Full-Stack Development": 85,
        "Cloud Architecture": 70,
        "Database Engineering": 60,
    }
    
    context = {
        "courses": mycourses,
        "total_xp": total_xp,
        "xp_level": xp_level,
        "heatmap": heatmap,
        "skill_map": skill_map,
    }
    return render(request, "hub.html", context)


def pricing_page(request):
    return render(request, "pricing.html")


def privacy_policy_page(request):
    return render(request, "privacy_policy.html")


def terms_page(request):
    return render(request, "terms_of_service.html")


def blog_list(request):
    """
    Engineering Insights & Industry Tech Blog
    """
    posts = [
        {
            "id": 1,
            "title": "Scaling Distributed Microservices with Event-Driven Architecture",
            "category": "SYSTEM DESIGN",
            "read_time": "6 Min Read",
            "date": "04 Oct 2026",
            "author": "Alex Chen",
            "author_title": "Senior Staff Architect",
            "avatar": "https://ui-avatars.com/api/?name=Alex+Chen&background=4f46e5&color=fff",
            "image": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=800&q=80",
            "excerpt": "Learn how top engineering teams decouple synchronous REST APIs using Kafka, event streaming, and transactional outbox patterns for 99.999% uptime."
        },
        {
            "id": 2,
            "title": "Building Production AI Pipelines with Python & Vector Databases",
            "category": "ARTIFICIAL INTELLIGENCE",
            "read_time": "8 Min Read",
            "date": "02 Oct 2026",
            "author": "Priya Sharma",
            "author_title": "AI Research Lead",
            "avatar": "https://ui-avatars.com/api/?name=Priya+Sharma&background=10b981&color=fff",
            "image": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=800&q=80",
            "excerpt": "A deep dive into Retrieval-Augmented Generation (RAG), embedding indexing with Qdrant, and orchestrating LLM agents at scale."
        },
        {
            "id": 3,
            "title": "Zero-Trust Cloud Security & Identity Protocol Best Practices",
            "category": "CLOUD & DEVOPS",
            "read_time": "5 Min Read",
            "date": "28 Sep 2026",
            "author": "David Kowalski",
            "author_title": "DevOps Architect",
            "avatar": "https://ui-avatars.com/api/?name=David+Kowalski&background=f43f5e&color=fff",
            "image": "https://images.unsplash.com/photo-1563986768609-322da13575f3?auto=format&fit=crop&w=800&q=80",
            "excerpt": "How to enforce strict IAM policies, automatic JWT key rotation, and ephemeral short-lived access credentials across Kubernetes clusters."
        },
        {
            "id": 4,
            "title": "Optimizing PostgreSQL Queries for Multi-Tenant SaaS Systems",
            "category": "DATABASE ENGINEERING",
            "read_time": "7 Min Read",
            "date": "24 Sep 2026",
            "author": "Sarah Jenkins",
            "author_title": "Principal Data Engineer",
            "avatar": "https://ui-avatars.com/api/?name=Sarah+Jenkins&background=7c3aed&color=fff",
            "image": "https://images.unsplash.com/photo-1544383835-bda2bc66a55d?auto=format&fit=crop&w=800&q=80",
            "excerpt": "Master index partitioning, connection pooling with PgBouncer, and query planner optimization for high-throughput relational workloads."
        }
    ]
    return render(request, "blog_list.html", {"posts": posts})


def blog_detail(request, pk):
    """
    Detailed Blog Article View with Author Metadata & Related Articles
    """
    posts_db = {
        1: {
            "id": 1,
            "title": "Scaling Distributed Microservices with Event-Driven Architecture",
            "category": "SYSTEM DESIGN",
            "read_time": "6 Min Read",
            "date": "04 Oct 2026",
            "author": "Alex Chen",
            "author_title": "Senior Staff Architect",
            "avatar": "https://ui-avatars.com/api/?name=Alex+Chen&background=4f46e5&color=fff",
            "image": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=800&q=80",
            "content": """
                <p class="lead fw-bold text-dark">Traditional synchronous HTTP/REST architectures struggle under extreme load spikes and cascading service failures. Event-driven architecture (EDA) decouples producers from consumers using asynchronous message streams.</p>
                
                <h4 class="fw-bold text-dark mt-4 mb-3">1. The Transactional Outbox Pattern</h4>
                <p>When updating a database record and publishing an event simultaneously, dual-write failures can lead to data inconsistency. The Outbox pattern solves this by writing the domain entity and an outbox event in the same atomic database transaction.</p>
                
                <h4 class="fw-bold text-dark mt-4 mb-3">2. Message Streaming with Apache Kafka</h4>
                <p>By leveraging log-based message brokers like Apache Kafka, services achieve high throughput, message replay capabilities, and strong partition ordering guarantees essential for financial and inventory processing systems.</p>

                <h4 class="fw-bold text-dark mt-4 mb-3">3. Idempotent Event Handlers</h4>
                <p>Because network retries can deliver duplicate messages, every subscriber node must enforce idempotency keys to ensure processing an event multiple times yields the exact same state result.</p>
            """
        },
        2: {
            "id": 2,
            "title": "Building Production AI Pipelines with Python & Vector Databases",
            "category": "ARTIFICIAL INTELLIGENCE",
            "read_time": "8 Min Read",
            "date": "02 Oct 2026",
            "author": "Priya Sharma",
            "author_title": "AI Research Lead",
            "avatar": "https://ui-avatars.com/api/?name=Priya+Sharma&background=10b981&color=fff",
            "image": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=800&q=80",
            "content": """
                <p class="lead fw-bold text-dark">Generative AI models excel at reasoning, but require real-world contextual grounding to eliminate hallucinations. RAG pipelines combine vector semantic search with large language models.</p>
                
                <h4 class="fw-bold text-dark mt-4 mb-3">1. High-Dimensional Vector Embeddings</h4>
                <p>Unstructured text, code repositories, and documentation are converted into dense vector representations using state-of-the-art embedding models, capturing deep semantic relationships rather than exact keyword matches.</p>

                <h4 class="fw-bold text-dark mt-4 mb-3">2. Vector Indexing Techniques</h4>
                <p>Hierarchical Navigable Small World (HNSW) graphs and Inverted File (IVF) indexes enable sub-millisecond similarity search queries over millions of high-dimensional document vectors.</p>
            """
        },
        3: {
            "id": 3,
            "title": "Zero-Trust Cloud Security & Identity Protocol Best Practices",
            "category": "CLOUD & DEVOPS",
            "read_time": "5 Min Read",
            "date": "28 Sep 2026",
            "author": "David Kowalski",
            "author_title": "DevOps Architect",
            "avatar": "https://ui-avatars.com/api/?name=David+Kowalski&background=f43f5e&color=fff",
            "image": "https://images.unsplash.com/photo-1563986768609-322da13575f3?auto=format&fit=crop&w=800&q=80",
            "content": """
                <p class="lead fw-bold text-dark">Never trust, always verify. Zero-Trust security assumes that network perimeters are breached and enforces continuous cryptographic authentication across all workloads.</p>
                
                <h4 class="fw-bold text-dark mt-4 mb-3">1. Ephemeral Workload Identity</h4>
                <p>Eliminate long-lived API keys and passwords. Use OAuth2 OIDC federation and SPIFFE/SPIRE to issue short-lived cryptographic x509 certificates directly to container workloads.</p>
            """
        },
        4: {
            "id": 4,
            "title": "Optimizing PostgreSQL Queries for Multi-Tenant SaaS Systems",
            "category": "DATABASE ENGINEERING",
            "read_time": "7 Min Read",
            "date": "24 Sep 2026",
            "author": "Sarah Jenkins",
            "author_title": "Principal Data Engineer",
            "avatar": "https://ui-avatars.com/api/?name=Sarah+Jenkins&background=7c3aed&color=fff",
            "image": "https://images.unsplash.com/photo-1544383835-bda2bc66a55d?auto=format&fit=crop&w=800&q=80",
            "content": """
                <p class="lead fw-bold text-dark">Multi-tenant database architectures require strict isolation, fast index scan times, and predictable resource allocation across all tenant schemas.</p>
                
                <h4 class="fw-bold text-dark mt-4 mb-3">1. Declarative Table Partitioning</h4>
                <p>Partitioning massive tables by tenant_id or date range keeps index trees small enough to fit inside RAM, drastically reducing disk I/O latency for read-heavy analytical queries.</p>
            """
        }
    }
    
    post = posts_db.get(int(pk), posts_db[1])
    return render(request, "blog_detail.html", {"post": post})