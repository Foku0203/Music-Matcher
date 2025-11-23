# accounts/models.py (ฉบับสมบูรณ์)

from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        # 1. ตรวจสอบว่าชื่อนี้ถูกต้อง
        related_name="custom_user_groups",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        # 2. ตรวจสอบว่าชื่อนี้ถูกต้อง และไม่ซ้ำกับข้างบน
        related_name="custom_user_permissions",
        related_query_name="user",
    )

    def __str__(self):
        return self.username