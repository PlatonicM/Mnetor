from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
import uuid
from django.contrib.auth.models import User
#from .models import Courses 


User = get_user_model()


# COURSES & LESSONS
class Courses(models.Model):
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    #category = models.ForeignKey(Category', on_delete=models.CASCADE, related_name='courses')
    price = models.IntegerField()
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="productImages/", blank=True, null=True)

    instructor = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="courses_taught"
    )

    class Meta:
        db_table = "Courses"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def avg_rating(self):
        agg = self.ratings.aggregate(models.Avg("rating"))
        return round(agg.get("rating__avg") or 0, 1)



class UserCourseMapping(models.Model):
    # Link to the User Node
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrolled_courses")
    
    # Link to the Course Node
    course = models.ForeignKey(Courses, on_delete=models.CASCADE)
    
    # Telemetry Data
    progress = models.IntegerField(default=0)  # Percentage 0-100
    is_completed = models.BooleanField(default=False)
    
    # System Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Prevents a user from having the same course mapped twice
        unique_together = ('user', 'course')
        verbose_name = "User Course Mapping"
        verbose_name_plural = "User Course Mappings"

    # Correct: Clean and modern
    def __str__(self):
        return f"{self.user.username} -> {self.course.name}"




class Lesson(models.Model):
    course = models.ForeignKey(Courses, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    video_url = models.URLField(blank=True, null=True)
    order = models.IntegerField(default=1)

    class Meta:
        db_table = "Lesson"
        ordering = ["order"]

    def __str__(self):
        return f"{self.course.name} - {self.title}"


# MY COURSES
class MyCourse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="my_courses")
    course = models.ForeignKey(Courses, on_delete=models.CASCADE, related_name="enrolled_users")
    progress = models.IntegerField(default=0)
    rating = models.IntegerField(default=0)
    lesson_count = models.IntegerField(default=0)
    completed_lessons = models.JSONField(default=list, blank=True)
    #created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "MyCourse"
        unique_together = ("user", "course")
        ordering = ["-id"]

    def __str__(self):
        return f"{self.user.username} - {self.course.name}"


# CART
class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cart_items")
    course = models.ForeignKey(Courses, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "CartItem"
        unique_together = ("user", "course")

    def __str__(self):
        return f"{self.user} cart → {self.course}"


# COURSE RATINGS
class CourseRating(models.Model):
    course = models.ForeignKey(Courses, on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(default=0)

    class Meta:
        db_table = "CourseRating"
        unique_together = ("course", "user")

    def __str__(self):
        return f"{self.user} → {self.course} ({self.rating})"


# ORDERS & INVOICES
class Order(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    total = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    payment_id = models.CharField(max_length=256, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "Order"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} - {self.user}"

    def mark_paid(self, payment_id=None):
        self.status = "PAID"
        self.payment_id = payment_id or self.payment_id
        self.paid_at = timezone.now()
        self.save()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    course = models.ForeignKey(Courses, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    qty = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "OrderItem"


class Invoice(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="invoice")
    invoice_number = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to="invoices/", blank=True, null=True)

    class Meta:
        db_table = "Invoice"
        ordering = ["-created_at"]

    def __str__(self):
        return self.invoice_number


# INSTRUCTOR + REVIEW + KYC
class InstructorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="instructor_profile")
    bio = models.TextField(blank=True)
    payout_email = models.EmailField(blank=True, null=True)
    verified = models.BooleanField(default=False)
    expertise = models.CharField(max_length=255, blank=True)

    twitter = models.URLField(blank=True)
    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)

    profile_image = models.ImageField(upload_to="instructors/", blank=True, null=True)

    class Meta:
        db_table = "InstructorProfile"

    def __str__(self):
        return self.user.username

    def avg_rating(self):
        agg = self.user.reviews_received.aggregate(models.Avg("rating"))
        return round(agg.get("rating__avg") or 0, 1)

    def courses_count(self):
        return self.user.courses_taught.count()

    def students_count(self):
        return MyCourse.objects.filter(course__in=self.user.courses_taught.all()).values("user").distinct().count()

    def badges(self):
        badges = []
        if self.verified:
            badges.append("verified")
        if self.avg_rating() >= 4.5:
            badges.append("top_rated")
        if self.courses_count() >= 5:
            badges.append("expert")
        return badges


class InstructorRequest(models.Model):
    STATUS = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="instructor_request")
    bio = models.TextField(blank=True)
    experience = models.CharField(max_length=255, blank=True)
    portfolio_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="PENDING")
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="reviewed_instructor_requests"
    )

    def __str__(self):
        return f"{self.user.username} - {self.status}"


class InstructorReview(models.Model):
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews_received")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews_given")
    rating = models.PositiveSmallIntegerField(default=5)
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("instructor", "user")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} → {self.instructor} ({self.rating})"


class KYCDocument(models.Model):
    DOC_TYPES = (
        ("AADHAAR", "Aadhaar"),
        ("PAN", "PAN"),
        ("PASSPORT", "Passport"),
        ("DRIVER", "Driving Licence"),
    )
    STATUS = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="kyc_documents")
    doc_type = models.CharField(max_length=20, choices=DOC_TYPES)
    file = models.FileField(upload_to="kyc/%Y/%m/%d/")
    front_image = models.ImageField(upload_to="kyc/thumbs/%Y/%m/%d/", blank=True, null=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="PENDING")
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="kyc_reviewed"
    )

    class Meta:
        ordering = ["-submitted_at"]
        db_table = "KYCDocument"

    def __str__(self):
        return f"{self.user} - {self.doc_type}"


# NOTIFICATIONS
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    url = models.CharField(max_length=400, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notification"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


# EVENTS
class EventCategory(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    ordering = models.IntegerField(default=0)

    class Meta:
        ordering = ["ordering", "name"]

    def __str__(self):
        return self.name


class Speaker(models.Model):
    name = models.CharField(max_length=200)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="speakers/", blank=True, null=True)
    linkedin = models.URLField(blank=True)
    twitter = models.URLField(blank=True)

    def __str__(self):
        return self.name


class Event(models.Model):
    STATUS = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(EventCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name="events")
    speakers = models.ManyToManyField(Speaker, blank=True, related_name="events")

    short_description = models.CharField(max_length=300, blank=True)
    description = models.TextField()
    image = models.ImageField(upload_to="events/", blank=True, null=True)

    start = models.DateTimeField(default=timezone.now)
    end = models.DateTimeField(default=timezone.now)

    capacity = models.PositiveIntegerField(default=100)
    status = models.CharField(max_length=20, choices=STATUS, default="draft")
    location = models.CharField(max_length=255, blank=True, null=True) # Add this line

    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-start"]

    def __str__(self):
        return self.title

    def is_full(self):
        return self.seats_taken() >= self.capacity

    def seats_taken(self):
        return self.registrations.filter(status="confirmed").count()

    def seats_left(self):
        return max(0, self.capacity - self.seats_taken())

    def get_absolute_url(self):
        return reverse("event_detail", args=[self.slug])

    def get_ics_url(self):
        return reverse("event_ics", args=[self.id])


class EventRegistration(models.Model):
    STATUS = [
        ("confirmed", "Confirmed"),
        ("waitlist", "Waitlist"),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="registrations")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS, default="waitlist")
    registered_at = models.DateTimeField(auto_now_add=True)
    promoted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-registered_at"]

    def __str__(self):
        return f"{self.name or self.user} → {self.event.title}"


class WaitlistEntry(models.Model):
    event = models.ForeignKey(Event, related_name="waitlist", on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.email


# CERTIFICATES
class Certificate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Courses, on_delete=models.CASCADE)

    cert_id = models.CharField(max_length=36, default=uuid.uuid4, editable=False)
    issued_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.course}"


class LessonComplete(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'lesson')

    def __str__(self):
        return f"{self.user} completed {self.lesson}"


# AUDIT / SESSIONS / CONTACT / SUBSCRIBER
class LoginActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="login_logs")
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    login_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "LoginActivity"
        ordering = ["-login_time"]

    def __str__(self):
        return f"{self.user} @ {self.login_time}"


class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    session_key = models.CharField(max_length=100, unique=True)
    user_agent = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    login_time = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True) 
    logout_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "UserSession"
        ordering = ["-login_time"]

    def __str__(self):
        return f"{self.user} session {self.session_key}"

    @property
    def duration(self):
        if not self.logout_time:
            return None
        return (self.logout_time - self.login_time).total_seconds()


class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    handled_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "ContactMessage"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.subject}"


class SubscriberEmail(models.Model):
    email = models.EmailField(unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed = models.BooleanField(default=False)

    class Meta:
        db_table = "SubscriberEmail"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")

    class Meta:
        db_table = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


#---------search model----------
class SearchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    query = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    

#----------submission-------------------------
class Submission(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('PASSED', 'Passed'),
        ('FAILED', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    # Link to your Course or Lesson model
    course = models.ForeignKey('Courses', on_delete=models.CASCADE, related_name='lab_submissions')
    title = models.CharField(max_length=255)  # e.g., "Python Lambda Lab"
    content = models.TextField(blank=True)   # Student's code or notes
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.status})"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
    # You could trigger a notification or a specialized XP log here