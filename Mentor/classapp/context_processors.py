from .models import Category, Notification
from django.db.models import Count

def global_header(request):
    # top categories (parent is null)
    top_categories = Category.objects.filter(parent__isnull=True).prefetch_related('children')[:30]
    notif_unread_count = 0
    recent_notifications = []
    if request.user.is_authenticated:
        notif_unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        recent_notifications = Notification.objects.filter(user=request.user).order_by("-created_at")[:6]
    return {
        "top_categories": top_categories,
        "notif_unread_count": notif_unread_count,
        "recent_notifications": recent_notifications,
    }
