import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils.timezone import now

from .models import (
    Courses, Lesson, MyCourse, CartItem, CourseRating,
    Order, OrderItem, Invoice, InstructorProfile,
    LoginActivity, UserSession, ContactMessage, SubscriberEmail,
    KYCDocument, Category, Notification, InstructorRequest, SearchHistory,
    Event, EventRegistration, EventCategory, Speaker,  UserCourseMapping,
    WaitlistEntry, Certificate, InstructorReview, LessonComplete 
)

# INLINE MODELS
class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ("order", "title", "video_url")
    ordering = ("order",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("course", "price", "qty")


# COURSES ADMIN
@admin.register(Courses)
class CoursesAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "price", "avg_rating")
    list_filter = ("category",)
    search_fields = ("name", "category__name")
    inlines = [LessonInline]
    ordering = ("name",)


# LESSON ADMIN
@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "title", "order")
    list_filter = ("course",)
    search_fields = ("course__name", "title")
    ordering = ("course", "order")


# MY COURSE ADMIN
@admin.register(MyCourse)
class MyCourseAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "course", "progress", "rating")
    list_filter = ("user", "course")
    search_fields = ("user__username", "course__name")
    readonly_fields = ("completed_lessons",)
    ordering = ("-id",)


# CART ADMIN
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "course", "added_at")
    list_filter = ("user", "course")
    search_fields = ("user__username", "course__name")
    ordering = ("-added_at",)


# COURSE RATING ADMIN
@admin.register(CourseRating)
class CourseRatingAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "course", "rating")
    list_filter = ("rating",)
    search_fields = ("user__username", "course__name")
    ordering = ("-id",)


# ORDER ADMIN
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "total", "payment_id", "created_at", "paid_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "payment_id")
    readonly_fields = ("created_at", "paid_at")
    inlines = [OrderItemInline]
    ordering = ("-id",)


# INVOICE ADMIN
@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "order", "order_user", "created_at")
    readonly_fields = ("created_at",)
    search_fields = ("invoice_number",)

    def order_user(self, obj):
        return obj.order.user.username
    order_user.short_description = "User"


# LOGIN ACTIVITY ADMIN
@admin.register(LoginActivity)
class LoginActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "ip_address", "login_time", "user_agent")
    list_filter = ("user",)
    search_fields = ("user__username", "ip_address")


# USER SESSION ADMIN
@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "session_key", "login_time", "logout_time", "duration")
    list_filter = ("user",)
    search_fields = ("user__username",)

    def duration(self, obj):
        """
        Calculated session duration.
        """
        if obj.logout_time:
            return obj.logout_time - obj.login_time
        return "Active"


# CONTACT MESSAGES + CSV EXPORT
def export_contacts_csv(modeladmin, request, queryset):
    """
    Admin action to download selected contact messages as CSV.
    """
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = "attachment; filename=contact_messages.csv"

    writer = csv.writer(resp)
    writer.writerow(["Name", "Email", "Subject", "Message", "IP", "Created"])

    for msg in queryset:
        writer.writerow([msg.name, msg.email, msg.subject, msg.message, msg.ip_address, msg.created_at])

    return resp

export_contacts_csv.short_description = "Export selected messages to CSV"


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "is_read", "ip_address", "created_at")
    list_filter = ("is_read",)
    search_fields = ("name", "email", "subject")
    readonly_fields = ("name", "email", "subject", "message", "ip_address", "created_at")

    actions = [export_contacts_csv, "mark_as_read", "mark_as_unread"]

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)


# SUBSCRIBER ADMIN
@admin.register(SubscriberEmail)
class SubscriberEmailAdmin(admin.ModelAdmin):
    list_display = ("email", "created_at", "ip_address", "confirmed")
    list_filter = ("confirmed",)
    search_fields = ("email",)


# INSTRUCTOR REQUEST ADMIN
@admin.register(InstructorRequest)
class InstructorRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "submitted_at", "reviewed_at")
    list_filter = ("status",)
    search_fields = ("user__username",)

    actions = ["approve_requests", "reject_requests"]

    def approve_requests(self, request, queryset):
        for req in queryset:
            req.status = "APPROVED"
            req.reviewed_by = request.user
            req.reviewed_at = now()
            req.save()
            InstructorProfile.objects.get_or_create(user=req.user)

    def reject_requests(self, request, queryset):
        queryset.update(status="REJECTED", reviewed_by=request.user, reviewed_at=now())


# KYC ADMIN
@admin.register(KYCDocument)
class KYCDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "doc_type", "status", "submitted_at", "reviewed_at")
    readonly_fields = ("submitted_at", "reviewed_at", "reviewed_by")
    list_filter = ("status", "doc_type")
    search_fields = ("user__username",)


# CATEGORY ADMIN
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


# NOTIFICATION ADMIN
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "is_read", "created_at")
    search_fields = ("title",)


# EVENT SYSTEM ADMIN
@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "ordering")
    ordering = ("ordering",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    list_display = ("name", "linkedin")
    search_fields = ("name",)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "start", "end", "capacity", "status")
    list_filter = ("status", "start")
    search_fields = ("title",)


# EVENT REGISTRATION
# @admin.register(EventRegistration)
# class EventRegistrationAdmin(admin.ModelAdmin):
#     list_display = ("event", "first_name", "display_name", "email", "status", "registered_at")
#     list_filter = ("status", "event")
#     search_fields = ("email", "first_name", "last_name", "user__username")

#     def display_name(self, obj):
#         return f"{obj.first_name} {obj.last_name}".strip()

@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    # 'get_first_name' and 'display_name' refer to the methods defined below
    list_display = ("event", "get_first_name", "display_name", "get_email", "status", "registered_at")
    list_filter = ("status", "event")
    
    # Use double underscores (__) to search related User fields
    search_fields = ("user__email", "user__first_name", "user__last_name", "user__username")

    # 1. Method to get First Name from related User
    @admin.display(description='First Name', ordering='user__first_name')
    def get_first_name(self, obj):
        return obj.user.first_name

    # 2. Method to get Email from related User
    @admin.display(description='Email', ordering='user__email')
    def get_email(self, obj):
        return obj.user.email

    # 3. Method for Full Display Name
    @admin.display(description='Full Name')
    def display_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username

    # Change List Template Handshake (Optional: if using your custom audit template)
    # change_list_template = "admin/classapp/eventregistration/change_list.html"

    

@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ("event", "name", "email", "created_at", "notified")
    list_filter = ("event",)


# CERTIFICATES
@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "cert_id", "issued_at")
    search_fields = ("user__username", "course__name")


# INSTRUCTOR REVIEW
@admin.register(InstructorReview)
class InstructorReviewAdmin(admin.ModelAdmin):
    list_display = ("instructor", "user", "rating", "created_at", "approved")
    list_filter = ("approved", "rating")
    search_fields = ("instructor__username", "user__username", "title", "body")

    actions = ["approve_reviews", "reject_reviews", "export_reviews_csv"]

    def approve_reviews(self, request, queryset):
        queryset.update(approved=True)

    def reject_reviews(self, request, queryset):
        queryset.update(approved=False)

    def export_reviews_csv(self, request, queryset):
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = "attachment; filename=instructor_reviews.csv"

        writer = csv.writer(resp)
        writer.writerow(["Instructor", "User", "Rating", "Title", "Body", "Created", "Approved"])

        for r in queryset:
            writer.writerow([
                r.instructor.username,
                r.user.username,
                r.rating,
                r.title,
                r.body,
                r.created_at,
                r.approved
            ])

        return resp


# INSTRUCTOR PROFILE ADMIN
@admin.register(InstructorProfile)
class InstructorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "bio")
    search_fields = ("user__username", "bio")


# LESSON COMPLETE ADMIN
@admin.register(LessonComplete)
class LessonCompleteAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "completed_on")
    list_filter = ("user", "lesson")
    search_fields = ("user__username", "lesson__title")


#-------------SearchHistoryAdmin-------------------
@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    # 1. UI Handshake: Columns to display in the list view
    list_display = ('query', 'user', 'ip_address', 'timestamp_formatted')
    
    # 2. Filter Node: Quick sidebar filters for deep analysis
    list_filter = ('timestamp', 'user')
    
    # 3. Search Protocol: Find specific queries or users
    search_fields = ('query', 'user__username', 'ip_address')
    
    # 4. Access Control: Data integrity (Analytics should usually be Read-Only)
    readonly_fields = ('query', 'user', 'ip_address', 'timestamp')
    
    # 5. Organization: Newest searches first
    ordering = ('-timestamp',)

    # Custom Column: Makes the timestamp look cleaner in the table
    def timestamp_formatted(self, obj):
        return obj.timestamp.strftime("%d %b %Y | %H:%M:%S")
    timestamp_formatted.short_description = 'Provisioned At'

    # Performance: Prevents slow queries if history gets huge
    show_full_result_count = False
    list_per_page = 50



# from django.contrib import admin
# from django.utils.html import format_html
# from .models import UserCourseMapping

# @admin.register(UserCourseMapping)
# class UserCourseMappingAdmin(admin.ModelAdmin):
#     list_display = ('user', 'course', 'display_progress', 'status_badge', 'created_at')
#     search_fields = ('user__username', 'course__name')
#     list_filter = ('is_completed', 'created_at', 'course')
#     readonly_fields = ('created_at', 'updated_at')
    
#     # 1. Custom Progress Telemetry with Color Coding
#     @admin.display(description='SYNC_PROGRESS', ordering='progress')
#     def display_progress(self, obj):
#         color = "#94a3b8" 
#         if obj.progress == 0:
#             color = "#ef4444" 
#         elif obj.progress < 100:
#             color = "#f59e0b" 
#         else:
#             color = "#10b981"

#         # CORRECT SYNTAX: Template string, then the variables
#         return format_html(
#             '<span style="color: {}; font-weight: 900; font-family: monospace;">{}%</span>',
#             color, obj.progress)

#     # 2. Visual Status Badge
#     @admin.display(description='STATUS')
#     def status_badge(self, obj):
#         if obj.is_completed:
#             return format_html('<span style="background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 5px; font-size: 10px; font-weight: bold;">COMPLETE</span>')
#         return format_html('<span style="background: #fef3c7; color: #92400e; padding: 2px 8px; border-radius: 5px; font-size: 10px; font-weight: bold;">ACTIVE</span>')

#     fieldsets = (
#         ('Identity Handshake', {
#             'fields': ('user', 'course')
#         }),
#         ('Telemetry Data', {
#             'fields': ('progress', 'is_completed')
#         }),
#         ('System Timestamps', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         }),
#     )


# @admin.register(UserCourseMapping)
# class UserCourseMappingAdmin(admin.ModelAdmin):
#     # 1. Reference the method name 'display_progress' in the list
#     list_display = ('user', 'course', 'display_progress', 'is_completed', 'created_at')
#     actions = ['reset_progress_protocol', 'force_complete_protocol']

#     # 2. Define the custom method to handle the string formatting
#     @admin.display(description='Progress %', ordering='progress')
#     def display_progress(self, obj):
#         return f"{obj.progress}%"

#     @admin.action(description="RESET_PROGRESS: Set selected nodes to 0%")
#     def reset_progress_protocol(self, request, queryset):
#         updated_count = queryset.update(progress=0, is_completed=False)
#         self.message_user(request, f"TERMINAL: {updated_count} nodes reset to initial state.")

#     @admin.action(description="FORCE_COMPLETE: Set selected nodes to 100%")
#     def force_complete_protocol(self, request, queryset):
#         updated_count = queryset.update(progress=100, is_completed=True)
#         self.message_user(request, f"TERMINAL: {updated_count} nodes synchronized to 100%.")