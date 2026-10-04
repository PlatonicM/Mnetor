from .models import Category, Notification, UserProfile
from django.db.models import Count

def global_header(request):
    top_categories = Category.objects.filter(parent__isnull=True).prefetch_related('children')[:30]
    notif_unread_count = 0
    recent_notifications = []
    user_avatar_url = ""
    user_profile = None

    if request.user.is_authenticated:
        notif_unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        recent_notifications = Notification.objects.filter(user=request.user).order_by("-created_at")[:6]
        
        try:
            user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
            if user_profile and user_profile.profile_image:
                user_avatar_url = user_profile.profile_image.url
        except Exception:
            pass

        if not user_avatar_url and hasattr(request.user, 'profile_image') and request.user.profile_image:
            try:
                user_avatar_url = request.user.profile_image.url
            except Exception:
                pass

        if not user_avatar_url:
            user_avatar_url = f"https://ui-avatars.com/api/?name={request.user.username}&background=4f46e5&color=fff"

    return {
        "top_categories": top_categories,
        "notif_unread_count": notif_unread_count,
        "unread_notifications_count": notif_unread_count,
        "recent_notifications": recent_notifications,
        "user_avatar_url": user_avatar_url,
        "user_profile": user_profile,
    }
