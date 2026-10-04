# classapp/admin_dashboard_views.py
from io import BytesIO
from datetime import datetime, timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseForbidden
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.utils import timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from django.contrib.auth import get_user_model
from .models import Order, OrderItem, Courses

User = get_user_model()

# --- FIGMA COLOR TOKENS ---
CLR_PRIMARY = '#6366f1'   # Indigo 500
CLR_SUCCESS = '#10b981'   # Emerald 500
CLR_SLATE = '#94a3b8'     # Slate 400

# ADMIN DASHBOARD CORE
@login_required
def admin_dashboard(request):
    """Provides high-fidelity operational metrics exclusively for authorized admin nodes."""
    user_email = (request.user.email or '').strip().lower()
    
    # Strict Authorization Gate: Only agentforge29@gmail.com or superusers allowed
    if not (user_email == "agentforge29@gmail.com" or request.user.is_superuser or request.user.is_staff):
        return HttpResponseForbidden("<div style='font-family:sans-serif; text-align:center; padding:50px;'><h2>Access Denied 403</h2><p>Command Center access is strictly restricted to administrator accounts (agentforge29@gmail.com).</p><a href='/'>Return to Home</a></div>")

    # Auto-grant staff privileges to agentforge29@gmail.com if missing
    if user_email == "agentforge29@gmail.com" and not (request.user.is_staff and request.user.is_superuser):
        request.user.is_staff = True
        request.user.is_superuser = True
        request.user.save()

    total_courses = Courses.objects.count()
    total_students = Order.objects.values("user").distinct().count()
    raw_earnings = (
        Order.objects.filter(status="PAID").aggregate(Sum("total"))["total__sum"] or 0
    )
    total_earnings = f"{raw_earnings:,.2f}"

    recent_orders = Order.objects.select_related('user').order_by("-created_at")[:10]

    top_courses_qs = (
        OrderItem.objects.values("course__id", "course__name")
        .annotate(
            sales=Count("id"),
            revenue=Sum("price")
        )
        .order_by("-revenue")[:6]
    )
    top_courses = []
    for tc in top_courses_qs:
        course_name = tc.get('course__name') or f"Course #{tc.get('course__id')}"
        revenue_val = float(tc.get('revenue') or 0)
        top_courses.append({
            'course__name': course_name,
            'name': course_name,
            'revenue': f"{revenue_val:,.2f}"
        })

    # Search & Category Filter Query
    search_q = request.GET.get('q', '').strip()
    category_f = request.GET.get('category', '').strip()

    from django.db.models import Q
    courses_qs = Courses.objects.all()

    if search_q:
        courses_qs = courses_qs.filter(Q(name__icontains=search_q) | Q(category__icontains=search_q))

    if category_f:
        courses_qs = courses_qs.filter(category__icontains=category_f)

    all_courses = list(courses_qs.order_by('-id')[:12])

    # Distinct categories for filter dropdown
    categories_list = Courses.objects.values_list('category', flat=True).distinct()
    categories = sorted(list(set(cat for cat in categories_list if cat)))

    all_users = User.objects.all().order_by('-date_joined')[:20]

    return render(request, "admin/dashboard_admin.html", {
        "total_courses": total_courses,
        "total_students": total_students,
        "total_earnings": total_earnings,
        "recent_orders": recent_orders,
        "top_courses": top_courses,
        "all_courses": all_courses,
        "all_users": all_users,
        "search_q": search_q,
        "category_f": category_f,
        "categories": categories
    })


# SYSTEM SALES CHART (Optimized Truncation)
@login_required
def admin_sales_chart(request):
    """Generates a spline-style bar chart using Figma design tokens."""
    user_email = (request.user.email or '').strip().lower()
    if not (user_email == "agentforge29@gmail.com" or request.user.is_superuser or request.user.is_staff):
        return HttpResponseForbidden("Node Access Denied")

    twelve_months_ago = timezone.now() - timedelta(days=365)
    
    # DB Optimization: Aggregate everything in 1 query using TruncMonth
    sales_data = (
        Order.objects.filter(status="PAID", created_at__gte=twelve_months_ago)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total=Sum('total'))
        .order_by('month')
    )

    labels = [d['month'].strftime("%b %y") for d in sales_data]
    values = [float(d['total']) for d in sales_data]

    # Chart Styling Node
    fig, ax = plt.subplots(figsize=(10, 4), facecolor='none')
    bars = ax.bar(labels, values, color=CLR_PRIMARY, alpha=0.85, width=0.6, edgecolor=CLR_PRIMARY, linewidth=1)
    
    # Aesthetic Handshakes
    ax.set_title("Revenue Velocity (Last 12 Months)", fontsize=14, fontweight='bold', pad=20, color='#0f172a')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#e2e8f0')
    ax.spines['bottom'].set_color('#e2e8f0')
    ax.tick_params(colors=CLR_SLATE, labelsize=9)
    
    plt.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, transparent=True)
    plt.close(fig)
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type="image/png")


# INSTRUCTOR ANALYTICS SPLINE (High-Fidelity)
@login_required
def instructor_analytics_chart(request):
    """Generates a liquid spline line chart for mentor tracking."""
    if not hasattr(request.user, "instructor_profile"):
        return HttpResponseForbidden("Node Access Denied")

    courses = Courses.objects.filter(trainer=request.user)
    twelve_months_ago = timezone.now() - timedelta(days=365)

    # DB Optimization Handshake
    earnings_data = (
        OrderItem.objects.filter(
            course__in=courses, 
            order__status="PAID", 
            order__created_at__gte=twelve_months_ago
        )
        .annotate(month=TruncMonth('order__created_at'))
        .values('month')
        .annotate(total=Sum('price'))
        .order_by('month')
    )

    labels = [d['month'].strftime("%b %y") for d in earnings_data]
    values = [float(d['total']) for d in earnings_data]

    # Spline Chart Handshake
    fig, ax = plt.subplots(figsize=(10, 4), facecolor='none')
    ax.plot(labels, values, marker="o", color=CLR_SUCCESS, linewidth=3, markersize=8, markerfacecolor='white', markeredgewidth=2)
    ax.fill_between(labels, values, color=CLR_SUCCESS, alpha=0.1)

    # UI Cleanup
    ax.set_title("Personal Revenue spline", fontsize=12, fontweight='800', color='#0f172a', loc='left')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    ax.tick_params(axis='both', which='major', labelsize=8, colors=CLR_SLATE)
    
    plt.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, transparent=True)
    plt.close(fig)
    buf.seek(0)

    return HttpResponse(buf.getvalue(), content_type="image/png")