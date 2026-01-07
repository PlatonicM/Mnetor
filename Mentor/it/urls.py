# from django.contrib import admin
# from django.urls import path, include
# from django.conf import settings
# from django.conf.urls.static import static

# # from django.conf.urls import handler404

# # # Point the handler to a view
# # handler404 = 'core.views.custom_404_view'

# handler404 = 'classapp.views.custom_404_view' # Update 'classapp' to your actual app name

# urlpatterns = [
#     path('admin/', admin.site.urls),

#     # Your main application
#     path('', include('classapp.urls')),
#     #path('accounts/', include('it.urls')),
#     #path("newsletter/", include("subscriber.urls")),

# ]

# # Media Files
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# # Static Files
# if settings.DEBUG:
#     urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# GLOBAL ERROR HANDLER PROTOCOL
# Note: This will only trigger when DEBUG = False
handler404 = 'classapp.views.custom_404_view'

urlpatterns = [
    # Identity & Admin Node
    path('admin/', admin.site.urls),

    # Core Curriculum Node
    path('', include('classapp.urls')),
    
    # Optional: Newsletter/Account Nodes (Uncomment as needed)
    # path('accounts/', include('it.urls')),
    # path("newsletter/", include("subscriber.urls")),
]

# STATIC & MEDIA SERVING HANDSHAKE
# Optimized for local development on high-resolution displays
if settings.DEBUG:
    # Serving uploaded curriculum assets (Course images, etc.)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Serving local design assets (CSS, JS, User icons)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# NODE_INFO: Ensure 'classapp.views.custom_404_view' exists
# to prevent "AttributeError" during the handshake.
