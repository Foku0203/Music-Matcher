from django.apps import AppConfig

class MatcherConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'matcher'
    verbose_name = "Music Matcher Application"  # ชื่อแอปที่แสดงใน Django Admin