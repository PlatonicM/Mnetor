from django.urls import path, include
from . import views, admin_dashboard_views
from .views import health_check

urlpatterns = [

    # 01. SYSTEM CORE HANDSHAKE
    path('', views.home, name='home'),
    path('about/', views.about_page, name='about'),
    path('contact/', views.contact_page, name='contact'),
    path('blog/', views.blog_list, name='blog_list'),
    path('blog/<int:pk>/', views.blog_detail, name='blog_detail'),
    path('search/', views.search, name='search'),
    path("subscribe/", views.subscribe_ajax, name="subscribe_ajax"),

    # 02. CURRICULUM NODES (Courses & Lessons)
    path('courses/', views.courses, name='courses'),
    path('course/<str:cid>/', views.course_detail, name='course_detail'),
    path("course/<str:course_id>/lesson/<str:lesson_id>/complete/", views.mark_lesson_complete, name="mark_lesson_complete"),
    
    # Lesson Progress & Interaction Nodes
    path('course/progress/<str:cid>/', views.update_progress, name='update_progress'),
    path('course/rate/<str:cid>/', views.rate_course, name='rate_course'),
    path('course/<str:course_id>/certificate/', views.download_certificate, name='download_certificate'),
    path('verify/cert/<str:cert_id>/', views.verify_certificate, name='verify_certificate'),

    path('api/dashboard/telemetry/', views.dashboard_telemetry_api, name='dashboard_telemetry_api'),
    
    # AJAX Data Handshakes
    path('ajax/courses/all/', views.ajax_all_courses, name='ajax_all_courses'),

    # 03. LEARNER INTERFACE (Personal Sync)
    path("my-curriculum/", views.my_courses, name="mycourses"),
    path("hub/", views.hub_page, name="hub"),
    path("my-curriculum/remove/<str:pk>/", views.remove_mycourse, name="remove_mycourse"),
    path('dashboard/remove-node/<str:course_id>/', views.remove_from_dashboard, name='remove_from_dashboard'),

    # 04. TRANSACTION PROTOCOLS (Commerce)
    path('cart/', views.cart, name='cart'),
    path('cart/add/<str:cid>/', views.add_to_cart, name='add_to_cart'),   
    path("cart/remove/<str:cid>/", views.remove_from_cart, name="remove_from_cart"),
    
    path("checkout/", views.checkout_page, name="checkout"),
    path('checkout/process/', views.checkout_process, name='checkout_process'),
    path('checkout/success/', views.checkout_success, name='checkout_success'),
    
    path("invoice/download/<str:order_id>/", views.download_invoice, name="download_invoice"),
    path('pricing/', views.pricing_page, name='pricing'),
    path('privacy/', views.privacy_policy_page, name='privacy_policy'),
    path('terms/', views.terms_page, name='terms_of_service'),
    path('membership/<slug:plan_slug>/', views.select_plan, name='select_plan'),

    # 05. IDENTITY & SECURITY NODES (Real Email 4-Digit OTP Auth)
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_form, name='login'),
    path('identity/login/', views.login_form, name='login_alias'),
    path('identity/logout/', views.logout_page, name='logout'),
    path('send-otp/', views.send_otp, name='send_otp'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('auth/google/', views.google_login, name='google_login'),
    path('identity/account/send-delete-otp/', views.send_delete_otp, name='send_delete_otp'),
    path('identity/account/verify-delete-otp/', views.verify_delete_otp, name='verify_delete_otp'),
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
    path("mentor/kyc/<str:pk>/audit/", views.kyc_detail, name="kyc_detail"),
    
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
    path("events/sync/<str:event_id>/register/", views.register_event, name="event_register"),
    path("events/sync/<str:event_id>/calendar-node/", views.event_ics, name="event_ics"),
    path("events/verify/<str:code>/", views.confirm_guest_registration, name="confirm_guest"),

    # 09. REAL-TIME SIGNAL NODES (Notifications)
    path('notifications/', views.notifications_all, name='notifications_all'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/pulse/', views.notifications_api, name='notifications_api'),
    path('notifications/ack/', views.notifications_mark_read, name='notifications_mark_read'),
    path('notifications/ack/', views.acknowledge_notification, name='notification_ack'),
    
    path('buynow/<str:course_id>/<str:user_id>/', views.buy_now, name='buynow'),
    
    # --- Mentor Control Room ---
    path('mentor/review/', views.mentor_review_list, name='mentor_review_list'),
    path('mentor/review/update/<str:submission_id>/', views.update_submission_status, name='update_submission_status'),

    # --- Student Laboratory ---
    path('lab/submit/', views.submit_lab, name='submit_lab'),
    path('course/<str:course_id>/lab/submit/', views.submit_lab, name='submit_lab_with_id'),
    
    # --- ICS & Calendar Provisioning ---
    path('event/ics/<str:event_id>/', views.event_ics, name='event_ics'),

    path('subscribe/initialize/', views.subscribe_node, name='subscribe_node'),
    path('health/', health_check, name='health_check'),
    path('dashboard/', views.student_dashboard, name='dashboard'),
    path('workspace/settings/update/', views.update_profile_view, name='update_profile'),
]
