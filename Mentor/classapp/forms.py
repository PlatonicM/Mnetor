from django import forms
from django.contrib.auth import get_user_model, authenticate
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

from .models import (
    InstructorProfile,
    SubscriberEmail,
    KYCDocument,
    InstructorReview
)
from django import forms
from .models import Event
from django.utils.text import slugify

User = get_user_model()

# Allowed uploads
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "application/pdf"]
MAX_UPLOAD_SIZE = 4 * 1024 * 1024  # 4MB


# SIGNUP FORM  (supports superuser options)
class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, min_length=6)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput, min_length=6)

    # Superuser-only optional fields
    is_staff = forms.BooleanField(required=False)
    is_superuser = forms.BooleanField(required=False)
    
    payout_email = forms.EmailField(required=False)
    bio = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
        )

    # UNIQUE VALIDATION
    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise ValidationError("Username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email already registered.")
        return email

    # PASSWORD VALIDATION
    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password")
        p2 = cleaned.get("password2")

        # Match passwords
        if p1 != p2:
            self.add_error("password2", "Passwords do not match.")

        # Django’s password strength validation
        if p1:
            try:
                validate_password(p1)
            except ValidationError as e:
                self.add_error("password", e)

        return cleaned

    # SAVE METHOD
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()

        return user


# LOGIN FORM
class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get("username")
        password = cleaned.get("password")

        user = authenticate(username=username, password=password)
        if not user:
            raise ValidationError("Invalid username or password.")

        cleaned["user"] = user
        return cleaned


# PROFILE UPDATE FORM
class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exclude(id=self.instance.id).exists():
            raise ValidationError("Email already in use.")
        return email


# CHANGE PASSWORD FORM
class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(widget=forms.PasswordInput)
    new_password = forms.CharField(widget=forms.PasswordInput)
    confirm_new_password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old = self.cleaned_data["old_password"]
        if not self.user.check_password(old):
            raise ValidationError("Old password is incorrect.")
        return old

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("new_password")
        p2 = cleaned.get("confirm_new_password")

        if p1 != p2:
            self.add_error("confirm_new_password", "New passwords do not match.")

        try:
            validate_password(p1, user=self.user)
        except ValidationError as e:
            self.add_error("new_password", e)

        return cleaned

    def save(self):
        self.user.set_password(self.cleaned_data["new_password"])
        self.user.save()
        return self.user


# INSTRUCTOR PROFILE FORM
class InstructorProfileForm(forms.ModelForm):
    class Meta:
        model = InstructorProfile
        fields = ("bio",)

    def clean_bio(self):
        bio = self.cleaned_data.get("bio", "")
        if len(bio) < 20:
            raise ValidationError("Bio must be at least 20 characters long.")
        return bio



# SUBSCRIBE FORM
class SubscribeForm(forms.ModelForm):
    class Meta:
        model = SubscriberEmail
        fields = ["email"]


# KYC DOCUMENT FORM
class KYCDocumentForm(forms.ModelForm):
    class Meta:
        model = KYCDocument
        fields = ("doc_type", "file")

    def clean_file(self):
        f = self.cleaned_data.get("file")

        if not f:
            raise ValidationError("Please upload a document.")

        if f.content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationError("Invalid file type. Allowed: JPG, PNG, PDF.")

        if f.size > MAX_UPLOAD_SIZE:
            raise ValidationError("File too large! Max size is 4MB.")

        return f


# INSTRUCTOR REVIEW FORM
class InstructorReviewForm(forms.ModelForm):
    class Meta:
        model = InstructorReview
        fields = ("rating", "title", "body")
        widgets = {
            "rating": forms.NumberInput(attrs={"min": 1, "max": 5, "class": "form-control w-25"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get("rating")
        if not (1 <= rating <= 5):
            raise ValidationError("Rating must be between 1 and 5.")
        return rating



class EventCreationForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'category', 'description', 'start', 'end', 'location', 'capacity']

    def __init__(self, *args, **kwargs):
        # Extract the user from view handshake
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start")
        end = cleaned_data.get("end")

        if start and end:
            # 1. Logic Guard: End must be after Start
            if end <= start:
                self.add_error('end', "TEMPORAL_ERROR: Session cannot end before it starts.")

            # 2. Conflict Guard: Check for overlapping provisioned nodes
            conflicting_events = Event.objects.filter(
                mentor=self.user,
                status="PUBLISHED",
                start__lt=end,  # Existing starts before new one ends
                end__gt=start   # Existing ends after new one starts
            )

            # If editing an existing event, exclude it from the conflict check
            if self.instance.pk:
                conflicting_events = conflicting_events.exclude(pk=self.instance.pk)

            if conflicting_events.exists():
                raise ValidationError(
                    "SCHEDULING_CONFLICT: You already have a session provisioned during this time block."
                )
        
        return cleaned_data