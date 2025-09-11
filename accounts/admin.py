from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

admin.site.register(User, UserAdmin)
# Register your models here.    

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, Role, UserRole, UserSuspension

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    list_display = ("email","username","status","is_staff","date_joined")
    list_filter = ("status","is_staff")
    search_fields = ("email","username")
    ordering = ("-date_joined",)
    fieldsets = (
        (None, {"fields": ("email","username","password")}),
        ("Permissions", {"fields": ("is_active","is_staff","is_superuser","groups","user_permissions")}),
        ("Status", {"fields": ("status",)}),
        ("Important dates", {"fields": ("last_login","date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",),
                             "fields": ("email","username","password1","password2","status","is_staff","is_superuser")}),)

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name","created_at")
    search_fields = ("name",)

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user","role","assigned_at")

@admin.register(UserSuspension)
class UserSuspensionAdmin(admin.ModelAdmin):
    list_display = ("user","admin","suspended_at","lifted_at")
