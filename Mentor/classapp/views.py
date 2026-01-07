import time
import uuid
from io import BytesIO
from datetime import datetime
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
from weasyprint import HTML
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
    # Fetch the 5 most recent verified achievements
    recent_achievements = Certificate.objects.select_related('user', 'course').order_by('-issued_at')[:5]
    
    context = {
        'recent_achievements': recent_achievements,
        # ... your other home context ...
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
    # Central Identity Hub showing enrollment status.
    enrollments = MyCourse.objects.filter(user=request.user).select_related('course')
    context = {
        "user": request.user,
        "enrollment_count": enrollments.count(),
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
        "current_session_key": request.session.session_key,
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

# SIGNUP VIEW
def signup(request):
    
    # Initializes a standard User Node. Blocks superuser injection.
    # Performs an atomic DB write, initializes the session, and auto-logins.
    if request.method == "GET":
        form = SignupForm()
        return render(request, "signup.html", {"form": form})

    # POST: Process Registration Packet
    form = SignupForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Registration Denied: Data integrity check failed.")
        return render(request, "signup.html", {"form": form})

    try:
        # Use transaction.atomic to ensure the user and session are synced
        with transaction.atomic():
            # 1. Initialize Standard User Instance
            user = form.save(commit=False)

            # 2. Hard-Block Superuser Privileges
            # Force standard user status regardless of incoming POST data
            user.is_staff = False
            user.is_superuser = False
            
            # 3. Save User Node to DB
            user.save()

            # 4. Automatic Session Handshake
            # Authenticate and login the new normal user immediately
            # login(request, user)
            
            # 5. Persistent Session Data Logic
            # Example: Initializing workspace settings in the session cluster
            request.session['is_new_user'] = True
            request.session['provisioning_timestamp'] = str(user.date_joined)

        # 6. Success Handshake
        messages.success(request, f"IDENTITY PROVISIONED: Welcome {user.username}. Session initialized.")
        
        # Redirect directly to dashboard since user is now logged in
        return redirect("login")

    except Exception as e:
        # Catch any database sync or session encryption errors
        messages.error(request, f"SYSTEM_ERROR: Data synchronization failed. {str(e)}")
        return render(request, "signup.html", {"form": form})




# LOGIN VIEW
def login_form(request):
    
    # Initializes a secure authentication handshake for standard users.
    # Blocks Superuser nodes from entering the cluster.
    # 1. Node Active Check
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "GET":
        form = LoginForm()
        return render(request, "login.html", {"form": form})

    # 2. Authenticate Packet
    form = LoginForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Handshake Denied: Data integrity check failed.")
        return render(request, "login.html", {"form": form})

    user = form.cleaned_data.get("user")

    if user is not None:
        # --- FEATURE: SUPERUSER BLOCK PROTOCOL ---
        if user.is_superuser:
            messages.error(request, "ACCESS_DENIED: Admin nodes must use the secure terminal (Admin Panel).")
            return render(request, "login.html", {"form": form})
        
        # 3. Provision Session Node
        ensure_session_key(request)

        # 4. Finalize Standard User Login
        login(request, user)
        
        # 5. Persistent Session Flags
        request.session['access_level'] = 'standard_user'
        
        # 6. Automatic Routing to Home
        messages.success(request, f"IDENTITY_VERIFIED: Welcome, {user.username.upper()}.")
        return redirect("home")
    
    else:
        messages.error(request, "CRITICAL_ERROR: User node identity unknown.")
        return render(request, "login.html", {"form": form})



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
        user.first_name = request.POST.get("first_name")
        user.last_name = request.POST.get("last_name")
        user.email = request.POST.get("email")
        user.save()
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
    query = request.GET.get('search', '')
    category_slug = request.GET.get('category', 'all')
    
    # 1. ALWAYS initialize the variable first (The Fix)
    results = Courses.objects.all().order_by('-id') 

    # 2. Refine the queryset based on search
    if query:
        results = results.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query)
        )

    # 3. Refine further based on category
    if category_slug != 'all':
        # Ensure 'category__slug' matches your Category model field name
        results = results.filter(category__slug=category_slug)

    # Now 'results' is guaranteed to exist when we get here
    context = {
        "courses": results,
        "search_query": query,
        "active_category": category_slug,
        "total_results": results.count(),
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
    # 1. Fetch Course Node
    course = get_object_or_404(Courses, id=cid)
    lessons = Lesson.objects.filter(course=course).order_by("order")
    
    # 2. Verify Enrollment (Access Control)
    mycourse = MyCourse.objects.filter(user=request.user, course=course).first()
    
    # 3. Handle Empty Curriculum
    if not lessons.exists():
        return render(request, "course_detail.html", {
            "course": course,
            "error_mode": "No modules provisioned for this track."
        })

    # 4. Identify Current Active Lesson
    # If no lesson ID in URL, default to the first one in the sequence
    lesson_id = request.GET.get("lesson")
    if lesson_id:
        current_lesson = get_object_or_404(Lesson, id=lesson_id, course=course)
    else:
        current_lesson = lessons.first()

    # 5. Fetch Completion Data Node
    # Using LessonComplete model for better scalability than a list field
    completed_lessons = LessonComplete.objects.filter(
        user=request.user, 
        lesson__course=course
    ).values_list('lesson_id', flat=True)
    
    completed_ids = set(completed_lessons)

    # 6. Sequential Logic: Lock/Unlock Handshake
    # Premium Feature: Lessons stay locked until the previous one is 100% complete
    lesson_data = []
    can_access_next = True # The first lesson is always unlocked
    
    for lesson in lessons:
        is_completed = lesson.id in completed_ids
        is_locked = not can_access_next
        
        lesson_data.append({
            "lesson": lesson,
            "is_completed": is_completed,
            "is_locked": is_locked,
            "is_active": lesson.id == current_lesson.id
        })
        
        # Determine if the NEXT lesson in the loop should be unlocked
        # Logic: If current lesson is completed, open the next bridge
        can_access_next = is_completed

    # 7. Progress Analytics for Figma UI
    total_count = lessons.count()
    completed_count = len(completed_ids)
    progress_percent = int((completed_count / total_count) * 100) if total_count > 0 else 0

    return render(request, "course_detail.html", {
        "course": course,
        "current_lesson": current_lesson,
        "lesson_data": lesson_data,
        "mycourse": mycourse,
        "progress_percent": progress_percent,
        "completed_count": completed_count,
        "total_count": total_count,
    })


# # MARK LESSON COMPLETE
def mark_lesson_complete(request, course_id, lesson_id):
    user = request.user
    lesson = Lesson.objects.get(id=lesson_id)
    course = Courses.objects.get(id=course_id)

    # Save completion
    LessonComplete.objects.get_or_create(user=user, lesson=lesson)

    # Check all lessons completed
    total = Lesson.objects.filter(course=course).count()
    completed = LessonComplete.objects.filter(user=user, lesson__course=course).count()

    # 100% completed → create certificate
    if completed == total:
        Certificate.objects.get_or_create(user=user, course=course)

    return JsonResponse({"status": "ok"})

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
    pdf.drawString(80, 110, "Chief Executive Officer,  MentorLMS")
    
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
            'title': f"Certified in {certificate.course.name} | MentorLMS",
            'summary': f"I have successfully mastered the {certificate.course.name} professional track.",
            'source': 'MentorLMS'
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
@require_POST
def add_to_cart(request, cid):
    course = get_object_or_404(Courses, id=cid)

    # Avoid duplicate entries
    CartItem.objects.get_or_create(user=request.user, course=course)

    # If AJAX request → return redirect URL to checkout
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        cart_count = CartItem.objects.filter(user=request.user).count()
        return JsonResponse({
            "msg": "Added to cart!",
            "cart_count": cart_count,
            "redirect": "/checkout/"   # 👈 AUTO-REDIRECT TO CHECKOUT
        })

    # Non-AJAX → Directly redirect to checkout
    messages.success(request, "Added to cart!")
    return redirect("checkout")      # 👈 updated redirect
    


#-------------------------remove cart----------------------------
@login_required
@require_POST
def remove_from_cart(request, cid):
    # 1. Decommission the Course Node from User's Cart
    CartItem.objects.filter(user=request.user, course_id=cid).delete()

    # 2. Fetch Updated State for the Handshake
    items = CartItem.objects.filter(user=request.user).select_related('course')
    cart_count = items.count()
    
    # 3. Recalculate Financial Analytics
    subtotal = sum(item.course.price for item in items)
    gst_provision = round(float(subtotal) * 0.18, 2) # 18% GST
    final_total = subtotal + gst_provision

    # 4. Handle AJAX Response (Figma Fluid UI)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "status": "success",
            "message": "Node disconnected from bag",
            "cart_count": cart_count,
            "total": float(subtotal),
            "gst": float(gst_provision),
            "final_total": float(final_total),
        })

    # 5. Fallback for Standard Reload
    messages.success(request, "Course removed from your selection.")
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


#------------PROCESS ORDER--------------------
@login_required
def checkout_process(request):
    # Ensure this only handles AJAX POST requests from our Handshake form
    if request.method != "POST":
        return JsonResponse({'success': False, 'message': 'Invalid Handshake Protocol'}, status=400)

    # Use a transaction to ensure cart deletion and order creation happen together
    with transaction.atomic():
        items = CartItem.objects.filter(user=request.user).select_related("course")

        if not items.exists():
            return JsonResponse({'success': False, 'message': 'Cart is empty. Provisioning aborted.'})

        # Calculate Technical Totals
        total = sum(i.course.price for i in items)
        gst = round(total * 0.18, 2)
        # Added the 3.00 System Fee from your Figma UI
        final_total = round(total + gst + 3.00, 2)

        # 1. Create the Order Node (Fixing the Naive Datetime error)
        order = Order.objects.create(
            user=request.user,
            total=final_total,
            status="PAID",
            paid_at=timezone.now() # This is the fix for your previous error
        )

        # 2. Provision Order Items
        for ci in items:
            OrderItem.objects.create(
                order=order,
                course=ci.course,
                price=ci.course.price,
                qty=1
            )

        # 3. Clear the Cart Node
        items.delete()

    # Return success bit and the redirect URL for the JavaScript logic
    return JsonResponse({
        'success': True,
        'message': 'Handshake Successful',
        'redirect_url': reverse('checkout_success')
    })


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
        # Retrieve order and ensure it belongs to the active user
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return HttpResponse("Handshake verification failed. Node not found.", status=404)

    # === Initialize PDF Response ===
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Invoice_MENTOR_{order_id}.pdf"'
    
    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    generation_time = timezone.now()
    
    # --- 1. Colorful Cyber Watermark ---
    pdf.saveState()
    pdf.translate(width/2, height/2)
    pdf.rotate(45)
    pdf.setFont("Helvetica-Bold", 80)
    pdf.setFillColorRGB(0.97, 0.97, 1.0) 
    pdf.drawCentredString(0, 50, "SYSTEM VERIFIED")
    pdf.drawCentredString(0, -50, "MENTOR_HUB_PRO")
    pdf.restoreState()

    # --- 2. Modern Accent Ribbon (FIXED Path Logic) ---
    pdf.setFillColorRGB(0.31, 0.27, 0.90) # #4F46E5
    path = pdf.beginPath() # Fixed method name
    path.moveTo(width - 150, height)
    path.lineTo(width, height)
    path.lineTo(width, height - 150)
    path.close()
    pdf.drawPath(path, fill=1, stroke=0)

    # --- 3. Header & Brand Identity ---
    pdf.setFillColorRGB(0.06, 0.09, 0.16) 
    pdf.setFont("Helvetica-Bold", 32)
    pdf.drawString(50, height - 70, "MENTOR")
    pdf.setFillColorRGB(0.31, 0.27, 0.90)
    pdf.drawString(200, height - 70, "LMS")
    
    pdf.setFillColor(colors.darkgray)
    pdf.setFont("Courier-Bold", 9)
    # Fixed Python addition logic
    node_id = request.user.id + 8800 
    pdf.drawString(50, height - 88, f"SYSTEM NODE: #STN_{node_id}")
    pdf.drawString(50, height - 100, "PROTOCOL: SECURE_DATA_PROVISIONING")

    # --- 4. High-Fidelity AUTHORIZED Seal ---
    pdf.setStrokeColorRGB(0.02, 0.59, 0.41) 
    pdf.setLineWidth(1.5)
    pdf.setFillColor(colors.white)
    pdf.roundRect(width - 170, height - 85, 120, 55, 12, fill=1, stroke=1)
    
    pdf.setFillColorRGB(0.02, 0.59, 0.41)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawCentredString(width - 110, height - 55, "AUTHORIZED")
    pdf.setFont("Courier-Bold", 8)
    pdf.drawCentredString(width - 110, height - 72, f"ID: {order.paid_at.strftime('%H%M%S')}SRDTS")

    # --- 5. Billing & Metadata Nodes ---
    pdf.setFillColor(colors.black)
    y = height - 150
    
    pdf.setFillColorRGB(0.98, 0.98, 1.0)
    pdf.roundRect(50, y - 60, 220, 75, 10, fill=1, stroke=0)
    
    pdf.setFillColorRGB(0.06, 0.09, 0.16)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(65, y + 2, "BILLED TO :")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(65, y - 18, request.user.get_full_name() or request.user.username)
    pdf.setFillColor(colors.darkgray)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(65, y - 32, request.user.email)
    pdf.drawString(65, y - 44, f"STUDENT: {request.user.username.upper()}")

    pdf.setFillColorRGB(0.06, 0.09, 0.16)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawRightString(width - 50, y + 2, "TRANSACTION MANIFEST")
    pdf.setFont("Courier", 10)
    pdf.drawRightString(width - 50, y - 18, f"INVOICE: INV-{str(order_id).zfill(8)}")
    pdf.drawRightString(width - 50, y - 32, f"DATE: {order.paid_at.strftime('%d %b %Y').upper()}")
    pdf.setFillColorRGB(0.02, 0.59, 0.41)
    pdf.drawRightString(width - 50, y - 46, "STATUS: PAID")

    # --- 6. Table: Provisioned Curriculum Nodes ---
    y -= 100
    pdf.setFillColorRGB(0.06, 0.09, 0.16)
    pdf.roundRect(50, y, width - 100, 30, 8, fill=1, stroke=0)
    
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(65, y + 11, "SN")
    pdf.drawString(110, y + 11, "COURSES NAME")
    pdf.drawRightString(width - 70, y + 11, "VAL (INR)")
    
    y -= 30
    pdf.setFont("Helvetica", 10)
    serial_no = 1
    
    for item in order.items.all():
        if serial_no % 2 == 0:
            pdf.setFillColorRGB(0.97, 0.98, 1.0)
            pdf.rect(50, y - 10, width - 100, 25, fill=1, stroke=0)
        
        pdf.setFillColor(colors.black)
        pdf.setFont("Courier-Bold", 10)
        pdf.drawString(65, y, str(serial_no).zfill(2))
        pdf.setFont("Helvetica", 10)
        pdf.drawString(110, y, item.course.name.upper()[:55])
        pdf.drawRightString(width - 70, y, f"{item.price:,.2f}")
        
        y -= 25
        serial_no += 1

    # --- 7. Grand Total Commitment Node ---
    y -= 20
    pdf.setFillColorRGB(0.31, 0.27, 0.90) 
    pdf.roundRect(width - 230, y - 60, 180, 80, 15, fill=1, stroke=0)
    
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(width - 215, y, "SUB TOTAL")
    # Python subtraction fix
    subtotal = float(order.total) - 3.0
    pdf.drawRightString(width - 65, y, f"{subtotal:,.2f}")
    
    y -= 18
    pdf.setFont("Helvetica", 8)
    pdf.drawString(width - 215, y, "PLATFORM FEE")
    pdf.drawRightString(width - 65, y, "3.00")
    
    y -= 25
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(width - 215, y, "TOTAL")
    pdf.drawRightString(width - 65, y, f"INR  {order.total:,.2f}")

    # --- 8. Signature Hub ---
    sign_y = 150
    pdf.setFillColorRGB(0.31, 0.27, 0.90)
    pdf.setFont("Times-BoldItalic", 20)
    pdf.drawString(50, sign_y + 10, "MrunalMade") 
    
    pdf.setStrokeColorRGB(0.31, 0.27, 0.90)
    pdf.setLineWidth(1)
    pdf.line(50, sign_y + 5, 200, sign_y + 5)
    
    pdf.setFillColorRGB(0.06, 0.09, 0.16)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(50, sign_y - 12, "MRUNAL CHAUDHARI")
    pdf.setFont("Courier-Bold", 8)
    pdf.setFillColor(colors.darkgray)
    pdf.drawString(50, sign_y - 25, "CHIEF EXECUTIVE OFFICER || MENTORLMS")

    # --- 9. Handshake Footer ---
    pdf.setFillColorRGB(0.02, 0.59, 0.41) 
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawCentredString(width/2, 80, "COURSES BUYING SUCCESSFUL || THANK YOU! SEE YOU AGAIN!")
    
    pdf.setStrokeColorRGB(0.9, 0.9, 0.9)
    pdf.line(100, 65, width - 100, 65)
    
    pdf.setFillColor(colors.gray)
    pdf.setFont("Courier", 7)
    pdf.drawCentredString(width/2, 52, f"GENERATED ON: {generation_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    pdf.drawCentredString(width/2, 42, f"HASH: SHA256-{str(order.paid_at.timestamp()).replace('.','')}")

    pdf.showPage()
    pdf.save()

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
    pdf.drawString(40, height - 60, "MENTOR LMS - INVOICE")
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
            subject = "ACCESS GRANTED: Mentor LMS Cluster"
            message = f"Provisioning successful for node: {email}\n\nWelcome to the Mentor LMS ecosystem. Your subscription is now active on our technical cluster."
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
from icalendar import Calendar, Event as iEvent
import uuid

def event_ics(request, event_id):

    # Generates a high-fidelity .ics calendar invitation with 
    # synchronized meeting links and organization metadata.
    ev = get_object_or_404(Event, id=event_id)
    
    cal = Calendar()
    # Required for Outlook/Apple Calendar compatibility
    cal.add('prodid', '-//MentorLMS Cluster//mentorlms.com//')
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
    ical.add('uid', f"EVENT-{ev.id}-{uuid.uuid4().hex[:8]}@mentorlms.com")
    
    # 5. Organizer Node
    ical.add('organizer', f"MAILTO:{settings.DEFAULT_FROM_EMAIL}")
    
    cal.add_component(ical)
    
    # Response Handshake
    response = HttpResponse(cal.to_ical(), content_type='text/calendar')
    # Clean filename using slug or title
    filename = f"MentorLMS-Session-{ev.id}.ics"
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
    """
    High-fidelity dashboard node: Fetches enrolled courses and 
    synchronizes lesson counts using database annotations.
    """
    # 1. Fetch courses with an annotated 'total_lessons' count
    # This replaces the for-loop and avoids unnecessary .save() calls
    # courses = MyCourse.objects.filter(user=request.user).select_related('course').annotate(
    #     total_lessons=Count('course__lesson')
    # )
    qs = MyCourse.objects.filter(user=request.user).select_related('course').annotate(
        total_lessons=Count('course__lessons') 
    )

    for mc in qs:
        if mc.lesson_count != mc.total_lessons:
            mc.lesson_count = mc.total_lessons
            mc.save(update_fields=['lesson_count'])

    return render(request, "my_courses.html", {"courses": qs})
    # 2. Sync Logic: Update the field only if it differs from the database count
    # This handles the "Update if not set" requirement efficiently
    

    # # 3. Provision context for the UI
    # context = {
    #     "courses": courses,
    #     "enrolled_count": courses.count(),
    #     "completed_count": courses.filter(progress=100).count()
    # }

    # return render(request, "my_courses.html", context)


@require_POST
def remove_mycourse(request, pk):
    """
    Decommissions a course node from the user's dashboard.
    Supports both standard redirects and high-fidelity AJAX handshakes.
    """
    mycourse = get_object_or_404(MyCourse, pk=pk, user=request.user)
    course_name = mycourse.course.name
    mycourse.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            "success": True,
            "message": f"Node {course_name} successfully decommissioned.",
            "remaining_count": MyCourse.objects.filter(user=request.user).count()
        })

    return redirect("mycourses")


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
def submit_lab(request, course_id):
    """
    Lab Submission Node: Provisioning student work to the 
    mentor review queue.
    """
    course = get_object_or_404(Courses, id=course_id)
    
    # 1. Enrollment Guard: Ensure user has a MyCourse record
    is_enrolled = MyCourse.objects.filter(user=request.user, course=course).exists()
    if not is_enrolled:
        messages.error(request, "ACCESS_DENIED: You must be enrolled to submit labs.")
        return redirect('course_detail', slug=course.slug)

    if request.method == "POST":
        # 2. Data Extraction
        title = request.POST.get('lab_title')
        content = request.POST.get('lab_content') # student code or links
        
        # 3. Duplicate Prevention: Check if a pending submission already exists
        active_submission = Submission.objects.filter(
            user=request.user, 
            course=course, 
            status='PENDING'
        ).exists()
        
        if active_submission:
            messages.warning(request, "BUFFER_FULL: You already have a pending review for this track.")
            return redirect('dashboard')

        # 4. Create Submission Node
        Submission.objects.create(
            user=request.user,
            course=course,
            title=title,
            content=content,
            status='PENDING'
        )

        messages.success(request, "UPLOADING_COMPLETE: Your lab is now in the Mentor Review Queue.")
        return redirect('dashboard')

    return render(request, 'courses/submit_lab.html', {'course': course})


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
    Command Center: Main analytical hub for the student.
    """
    # 1. Fetch User Course Mappings (Active Tracks)
    user_courses = UserCourseMapping.objects.filter(user=request.user).select_related('course')
    
    # 2. Calculate Analytical Metrics
    avg_comp = user_courses.aggregate(Avg('progress'))['progress__avg'] or 0
    
    # 3. Dynamic XP Logic (Feature: System Gamification)
    completed_tracks = user_courses.filter(progress=100).count()
    xp_points = (completed_tracks * 1000) + (int(avg_comp) * 10)
    
    # 4. Infinite Rank Logic
    if xp_points > 5000:
        rank, color = "ARCHITECT", "#A855F7" # Purple
    elif xp_points > 2000:
        rank, color = "PROFESSIONAL", "#6366F1" # Indigo
    else:
        rank, color = "INITIATE", "#10B981" # Emerald

    # 5. Submission Telemetry
    recent_labs = Submission.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    context = {
        'courses': user_courses,
        'avg_comp': round(avg_comp, 1),
        'xp_level': rank,
        'xp_color': color,
        'total_xp': xp_points,
        'recent_labs': recent_labs,
        'node_id': uuid.uuid4().hex[:8].upper()
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
    """
    Protocol: IDENTITY_RECONFIGURATION_PAGE
    Handles full-page profile updates with system validation.
    """
    user = request.user
    
    if request.method == "POST":
        try:
            new_email = request.POST.get("email")
            
            # 1. Identity Validation (Email Collision Check)
            if User.objects.exclude(pk=user.pk).filter(email=new_email).exists():
                messages.error(request, "CRITICAL_ERROR: EMAIL_COLLISION Detected.")
                return render(request, "update.html")

            # 2. Update Registry
            user.first_name = request.POST.get("first_name", user.first_name)
            user.last_name = request.POST.get("last_name", user.last_name)
            user.email = new_email
            
            # 3. Handle Profile Image if provided
            if request.FILES.get("profile_image"):
                user.profile_image = request.FILES.get("profile_image")

            user.save()
            messages.success(request, "IDENTITY_SYNC_COMPLETE: Registry Updated.")
            return redirect('profile') # Redirect back to the Workspace/Profile Hub
            
        except Exception as e:
            messages.error(request, f"SYSTEM_FAULT: {str(e)}")
            return redirect('update_profile')

    # GET Request: Load the configuration interface
    return render(request, "update.html")