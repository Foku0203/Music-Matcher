from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# ===================== 1. USER MANAGEMENT =====================

class User(AbstractUser):
    status = models.CharField(max_length=20, default='Active')
    age = models.PositiveIntegerField(null=True, blank=True)
    gender_choices = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('LG', 'LGBTQ+')
    ]
    gender = models.CharField(max_length=10, choices=gender_choices, null=True, blank=True)

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    province = models.CharField(max_length=100, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.user.username

class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    def __str__(self):
        return self.name

class UserRole(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

class UserSuspension(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reason = models.TextField()
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

# ===================== 2. CATALOG & MUSIC =====================

class Artist(models.Model):
    artist_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    image_url = models.URLField(null=True, blank=True)

    def __str__(self):
        return self.name

class Album(models.Model):
    album_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    release_date = models.DateField(null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)

    def __str__(self):
        return self.title

class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50) 
    type = models.CharField(max_length=20, choices=[('MOOD', 'Mood'), ('GENRE', 'Genre')])

    def __str__(self):
        return f"{self.name} ({self.type})"
    
class Song(models.Model):
    song_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    album = models.ForeignKey(Album, on_delete=models.SET_NULL, null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    lyrics = models.TextField(null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)
    genius_url = models.URLField(null=True, blank=True)
    
    # Metadata
    json_mood = models.CharField(max_length=50, null=True, blank=True) 
    json_genre = models.CharField(max_length=100, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)

    # Spotify Data
    spotify_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    spotify_link = models.URLField(null=True, blank=True)

    # Audio Features
    valence = models.FloatField(default=0.5)
    energy = models.FloatField(default=0.5)
    tempo = models.FloatField(default=120.0)
    danceability = models.FloatField(default=0.5)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.artist.name}"

# ===================== 3. USER ACTIVITY =====================

class Interaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=[('like', 'Like'), ('dislike', 'Dislike'), ('skip', 'Skip')])
    rating = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class FavoriteSong(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

class UserScanLog(models.Model):
    scan_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    input_image = models.ImageField(upload_to='scan_uploads/')
    detected_emotion = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class PlayHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    detected_emotion = models.CharField(max_length=50, null=True)
    source = models.CharField(max_length=50, default='manual') 
    started_at = models.DateTimeField(auto_now_add=True)

# ===================== 4. PLAYLIST =====================

class Playlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class PlaylistItem(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)


# ===================== 5. AI MODEL SYSTEM =====================

class ModelVersion(models.Model):
    # --- Basic Info ---
    version = models.CharField(max_length=50)       # เช่น "Model v2"
    algorithm = models.CharField(max_length=100, default="Classification") 
    
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Training', 'Training'),
        ('Draft', 'Draft'),
        ('Archived', 'Archived'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft') 
    
    # --- Settings (Hyperparameters) ---
    data_split = models.CharField(max_length=50, default="80/10/10") 
    epoch = models.IntegerField(default=32)
    batch_size = models.IntegerField(default=10)
    activation = models.CharField(max_length=50, default='ReLU')
    learning_rate = models.FloatField(default=0.01)
    
    # Regularization
    regularization_type = models.CharField(max_length=10, choices=[('L1', 'L1'), ('L2', 'L2'), ('None', 'None')], default='L2')
    regularization_rate = models.FloatField(default=0.01)

    # --- Metrics ---
    accuracy = models.FloatField(default=0.0)      
    val_accuracy = models.FloatField(default=0.0)  
    ndcg_score = models.FloatField(default=0.0)    
    loss = models.FloatField(default=0.0)          

    # --- File ---
    model_file = models.FileField(upload_to='models/', null=True, blank=True) 
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.version} ({self.status})"

class Recommendation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    context_emotion = models.CharField(max_length=50)
    algorithm = models.CharField(max_length=100)
    score = models.FloatField(null=True, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

class RetrainJob(models.Model):
    job_id = models.AutoField(primary_key=True)
    model_version = models.ForeignKey(ModelVersion, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='Pending') # Pending, Running, Completed, Failed
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    log_message = models.TextField(blank=True, null=True) # เก็บ Error log

    def __str__(self):
        return f"Job {self.job_id} for {self.model_version.version}"

class TrainingLog(models.Model):
    """
    เก็บ Log การเทรนราย Epoch เพื่อเอาไปวาดกราฟ
    """
    model_version = models.ForeignKey(ModelVersion, on_delete=models.CASCADE, related_name='logs')
    epoch_number = models.IntegerField()  
    training_loss = models.FloatField()   
    validation_loss = models.FloatField() 
    training_acc = models.FloatField(null=True, blank=True)
    validation_acc = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['epoch_number']