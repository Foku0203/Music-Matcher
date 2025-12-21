from django import forms
from .models import Song

class SongForm(forms.ModelForm):
    class Meta:
        model = Song
        # เลือกเฉพาะฟิลด์ที่มีจริงใน Model ใหม่
        fields = ['title', 'artist', 'album', 'duration_sec', 'platform', 'external_id', 'is_active']
        
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'artist': forms.Select(attrs={'class': 'form-control'}),
            'album': forms.Select(attrs={'class': 'form-control'}),
            'duration_sec': forms.NumberInput(attrs={'class': 'form-control'}),
            'platform': forms.Select(attrs={'class': 'form-control'}),
            'external_id': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }