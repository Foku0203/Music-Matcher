from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    # ถ้าต้องการเพิ่ม field ใหม่ เช่น phone, gender สามารถเพิ่มได้
    # phone = models.CharField(max_length=15, blank=True, null=True)
    # gender = models.CharField(max_length=10, blank=True, null=True)
    pass
import uuid

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, username, password, **extra):
        if not email:
            raise ValueError("Email is required")
        if not username:
            raise ValueError("Username is required")
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email, username, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        extra.setdefault("status", User.Status.ACTIVE)
        return self._create_user(email, username, password, **extra)

    def create_superuser(self, email, username, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("status", User.Status.ACTIVE)
        if extra.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, username, password, **extra)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "active"
        SUSPENDED = "suspended", "suspended"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    username = models.CharField(max_length=50, unique=True, db_index=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    class Meta:
        db_table = "users"


class Role(TimeStampedModel):
    name = models.CharField(max_length=30, unique=True, db_index=True)
    class Meta:
        db_table = "roles"
    def __str__(self):
        return self.name


class UserRole(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_users")
    assigned_at = models.DateTimeField(default=timezone.now)
    class Meta:
        db_table = "user_roles"
        unique_together = ("user", "role")


class UserSuspension(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="suspensions")
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="issued_suspensions")
    reason = models.TextField(blank=True)
    suspended_at = models.DateTimeField(default=timezone.now)
    lifted_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        db_table = "user_suspensions"
