import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from django.utils.timezone import now


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # hashes password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "Admin")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=150, unique=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    role = models.CharField(max_length=50, null=True, blank=True)  # Example: Admin, Sales, Manager
    status = models.CharField(max_length=20, default ="Active")  # Example: Active, Inactive

    # Foreign key to department (assumes Department model exists)
    department_id = models.UUIDField(null=True, blank=True)

    created_by = models.UUIDField(null=True, blank=True)
    updated_by = models.UUIDField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=True)

    login_attempts = models.IntegerField(default=0, null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    last_failed_login_at = models.DateTimeField(null=True, blank=True)
    account_locked_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

# Optional: Login Log for auditing login attempts
class LoginLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    reason = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} - {'Success' if self.success else 'Failure'} at {self.timestamp}"



class UserSession(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='sessions')
    session_token = models.CharField(max_length=512, unique=True)  # Store JWT or custom token
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=now)
    last_seen_at = models.DateTimeField(default=now)
    is_active = models.BooleanField(default=True)  # Helpful for manual invalidation

    def __str__(self):
        return f"{self.user.email} @ {self.ip_address} ({self.created_at})"
