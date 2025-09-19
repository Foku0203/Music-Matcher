from django import forms
from .models import Song

class SongForm(forms.ModelForm):
    class Meta:
        model = Song
        fields = ["title", "artist", "album", "genres", "language", "release_date"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "w-full px-4 py-2 rounded-lg bg-gray-800 border border-gray-700 focus:border-blue-500 focus:ring focus:ring-blue-500/40"}),
            "artist": forms.Select(attrs={"class": "w-full px-4 py-2 rounded-lg bg-gray-800 border border-gray-700"}),
            "album": forms.Select(attrs={"class": "w-full px-4 py-2 rounded-lg bg-gray-800 border border-gray-700"}),
            "genres": forms.CheckboxSelectMultiple(attrs={"class": "hidden"}),  # เราจะ render เองให้เป็นปุ่ม
            "language": forms.Select(attrs={"class": "w-full px-4 py-2 rounded-lg bg-gray-800 border border-gray-700"}),
            "release_date": forms.DateInput(attrs={"class": "w-full px-4 py-2 rounded-lg bg-gray-800 border border-gray-700", "type": "date"}),
        }
