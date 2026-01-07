from django.urls import path, include
from . import views, admin_dashboard_views
from .views import health_check

urlpatterns = [

    # 01. SYSTEM CORE HANDSHAKE
    path('', views.home, name='home'),
    path('about/', views.about_page, name='about'),
    path('contact/', views.contact_page, name='contact'),
    path('search/', views.search, name='search'),
    path("subscribe/", views.subscribe_ajax, name="subscribe_ajax"),

    # 02. CURRICULUM NODES (Courses & Lessons)
    path('courses/', views.courses, name='courses'),
    path('course/<int:cid>/', views.course_detail, name='course_detail'),
    path("course/<int:course_id>/lesson/<int:lesson_id>/complete/", views.mark_lesson_complete, name="mark_lesson_complete"),
    
    # Lesson Progress & Interaction Nodes
    path('course/progress/<int:cid>/', views.update_progress, name='update_progress'),
    path('course/rate/<int:cid>/', views.rate_course, name='rate_course'),
    path('course/<int:course_id>/certificate/', views.download_certificate, name='download_certificate'),
    path('verify/cert/<int:cert_id>/', views.verify_certificate, name='verify_certificate'),
    #path('course/<int:course_id>/lesson/<int:lesson_id>/complete/', views.mark_lesson_complete, name='mark_lesson_complete'),

    path('api/dashboard/telemetry/', views.dashboard_telemetry_api, name='dashboard_telemetry_api'),
    
    # AJAX Data Handshakes
    path('ajax/courses/all/', views.ajax_all_courses, name='ajax_all_courses'),

    # 03. LEARNER INTERFACE (Personal Sync)
    path("my-curriculum/", views.my_courses, name="mycourses"),
    path("my-curriculum/remove/<int:pk>/", views.remove_mycourse, name="remove_mycourse"),
    path('dashboard/remove-node/<int:course_id>/', views.remove_from_dashboard, name='remove_from_dashboard'),

    # 04. TRANSACTION PROTOCOLS (Commerce)
    path('cart/', views.cart, name='cart'),
    path('cart/add/<int:cid>/', views.add_to_cart, name='add_to_cart'),   
    path("cart/remove/<int:cid>/", views.remove_from_cart, name="remove_from_cart"),
    
    path("checkout/", views.checkout_page, name="checkout"),
    path('checkout/process/', views.checkout_process, name='checkout_process'),
    path('checkout/success/', views.checkout_success, name='checkout_success'),
    
    path("invoice/download/<int:order_id>/", views.download_invoice, name="download_invoice"),
    path('membership/<slug:plan_slug>/', views.select_plan, name='select_plan'),

    # 05. IDENTITY & SECURITY NODES (Auth)
    #path('identity/signup/', views.signup, name='signup'),
    path('signup/', views.signup, name='signup'),
    path('identity/login/', views.login_form, name='login'),
    path('identity/logout/', views.logout_page, name='logout'),
    path("identity/recovery/", views.forgot_password, name="forgot_password"),

    # Profile Handshakes
    path("profile/", views.profile_page, name="profile"),
    path("profile/history/", views.profile_history, name="profile_history"),
    path("profile/sync-settings/", views.update_profile, name="update_profile"),
    path("profile/key-rotation/", views.change_password, name="change_password"),

    # 06. MENTOR OPS (Instructor Hub)
    path("trainers/", views.trainers_page, name="trainers"),
    path("mentor/dashboard/", views.instructor_dashboard, name="instructor_dashboard"),
    path("mentor/analytics/v1/", admin_dashboard_views.instructor_analytics_chart, name="instructor_analytics_chart"),
    path("mentor/apply/", views.request_instructor, name="request_instructor"),
    path("mentor/kyc/upload/", views.kyc_upload, name="kyc_upload"),
    path("mentor/kyc/<int:pk>/audit/", views.kyc_detail, name="kyc_detail"),
    
    # Public Mentor Nodes
    path("mentor/<str:username>/", views.instructor_detail, name="instructor_detail"),
    path("mentor/<str:username>/handshake-review/", views.instructor_review_create, name="instructor_review_create"),

    # 07. ADMIN COMMAND CENTER
    path("command-center/dashboard/", admin_dashboard_views.admin_dashboard, name="admin_dashboard"),
    path("command-center/metrics/sales.png", admin_dashboard_views.admin_sales_chart, name="admin_sales_chart"),

    # 08. EVENT CLUSTER HANDSHAKES
    path("events/", views.events_list, name="events"),
    path("events/create-node/", views.create_event, name="create_event"),
    path("events/<slug:slug>/", views.event_detail, name="event_detail"),
    path("events/sync/<int:event_id>/register/", views.register_event, name="event_register"),
    path("events/sync/<int:event_id>/calendar-node/", views.event_ics, name="event_ics"),
    path("events/verify/<str:code>/", views.confirm_guest_registration, name="confirm_guest"),

    # 09. REAL-TIME SIGNAL NODES (Notifications)
    path('notifications/', views.notifications_all, name='notifications_all'),
    path('notifications/', views.notifications_view, name='notifications'), # Add this line
    path('notifications/pulse/', views.notifications_api, name='notifications_api'),
    path('notifications/ack/', views.notifications_mark_read, name='notifications_mark_read'),
    path('notifications/ack/', views.acknowledge_notification, name='notification_ack'),
    
    path('buynow/<int:course_id>/<int:user_id>/', views.buy_now, name='buynow'),
    
    
    
    # --- Mentor Control Room ---
    path('mentor/review/', views.mentor_review_list, name='mentor_review_list'),
    
    # AJAX Handshake for grading
    path('mentor/review/update/<int:submission_id>/', views.update_submission_status, name='update_submission_status'),

    # --- Student Laboratory ---
    # View to submit a lab (if you haven't created it yet)
    path('course/<int:course_id>/lab/submit/', views.submit_lab, name='submit_lab'),
    
    # --- ICS & Calendar Provisioning ---
    path('event/ics/<int:event_id>/', views.event_ics, name='event_ics'),

    path('subscribe/initialize/', views.subscribe_node, name='subscribe_node'),
    
    path('health/', health_check, name='health_check'),

    path('dashboard/', views.student_dashboard, name='dashboard'),



    path('profile/', views.profile_page, name='profile'),
    #path('profile/update/', views.update_profile_ajax, name='update_profile'),
    path('workspace/settings/update/', views.update_profile_view, name='update_profile'),
    path('profile/history/', views.profile_history, name='profile_history'),
    path('profile/password/', views.change_password, name='change_password'),
]
