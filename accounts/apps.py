from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"       # ต้องเป็น "accounts"
    # ห้ามกำหนด label เอง
