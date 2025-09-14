# filepath: d:\Music Matcher\Music-Matcher\accounts\models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    # เพิ่มฟิลด์ที่คุณต้องการที่นี่ เช่น
    # bio = models.TextField(blank=True)

    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="custom_user_set",  # สำคัญ: เพิ่ม related_name เพื่อหลีกเลี่ยงความขัดแย้ง
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="custom_user_set",  # สำคัญ: เพิ่ม related_name เพื่อหลีกเลี่ยงความขัดแย้ง
        related_query_name="user",
    )

    def __str__(self):
        return self.username