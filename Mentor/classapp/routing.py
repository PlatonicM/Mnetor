# from django.urls import re_path
# from . import consumers

# websocket_urlpatterns = [
#     re_path(
#         r"ws/events/(?P<event_id>\d+)/$",
#         consumers.EventChatConsumer.as_asgi()
#     ),
# ]


from django.urls import re_path, path
from . import consumers

# --- OMEGA CLUSTER ROUTING ---
# These paths define the real-time handshake protocols for the platform.
# We use re_path for granular ID capture and path for global system nodes.

websocket_urlpatterns = [
    # 1. Event Node Handshake
    # Capture protocol: Captures numeric event ID for regional cluster syncing.
    re_path(
        r"ws/events/(?P<event_id>\d+)/sync/$", 
        consumers.EventChatConsumer.as_asgi()
    ),

    # 2. Global System Pulse (Feature 11: Real-time Radar)
    # Used for the 'System Omega' radar ping we built in the dashboard.
    path(
        "ws/system/pulse/", 
        consumers.SystemPulseConsumer.as_asgi()
    ),

    # 3. Mentor Identity Node (Feature 12: Private Mentor Sync)
    # Direct handshake between a student and an on-call mentor.
    re_path(
        r"ws/handshake/mentor/(?P<mentor_id>\w+)/$", 
        consumers.MentorChatConsumer.as_asgi()
    ),
]