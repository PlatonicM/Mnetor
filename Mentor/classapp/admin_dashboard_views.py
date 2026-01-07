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

from .models import Order, OrderItem, Courses

# --- FIGMA COLOR TOKENS ---
CLR_PRIMARY = '#6366f1'   # Indigo 500
CLR_SUCCESS = '#10b981'   # Emerald 500
CLR_SLATE = '#94a3b8'     # Slate 400

# ADMIN DASHBOARD CORE
@staff_member_required
def admin_dashboard(request):
    """Provides high-fidelity operational metrics for the system node."""
    total_courses = Courses.objects.count()
    total_students = Order.objects.values("user").distinct().count()
    total_earnings = (
        Order.objects.filter(status="PAID").aggregate(Sum("total"))["total__sum"] or 0
    )

    recent_orders = Order.objects.select_related('user').order_by("-created_at")[:8]

    top_courses = (
        OrderItem.objects.values("course__id", "course__name")
        .annotate(
            sales=Count("id"),
            revenue=Sum("price")
        )
        .order_by("-revenue")[:6]
    )

    return render(request, "admin/dashboard_admin.html", {
        "total_courses": total_courses,
        "total_students": total_students,
        "total_earnings": total_earnings,
        "recent_orders": recent_orders,
        "top_courses": top_courses,
    })


# SYSTEM SALES CHART (Optimized Truncation)
@staff_member_required
def admin_sales_chart(request):
    """Generates a spline-style bar chart using Figma design tokens."""
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