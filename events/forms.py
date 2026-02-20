"""Forms for the events app."""
from django import forms
from django.utils import timezone

from .models import Event, EventStatus, Genre, Venue


class EventSubmissionForm(forms.ModelForm):
    """
    Form for anonymous users to submit events.
    Events are created with pending status and require moderation.
    """

    # Use a datetime-local input for better UX
    datetime = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": "form-input",
            }
        ),
        help_text="Select the date and time of the event",
    )

    # Multi-select for genre tags
    genre_tags = forms.ModelMultipleChoiceField(
        queryset=Genre.objects.all().order_by("name"),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Genres",
    )

    class Meta:
        model = Event
        fields = ["name", "datetime", "venue", "artists", "genre_tags", "link", "notes"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Event name",
                }
            ),
            "venue": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "artists": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "placeholder": "Artist 1\nArtist 2\nArtist 3",
                    "rows": 4,
                }
            ),
            "link": forms.URLInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "https://...",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "placeholder": "Additional details...",
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order venues alphabetically
        self.fields["venue"].queryset = Venue.objects.all().order_by("name")
        self.fields["venue"].empty_label = "Select a venue..."

    def clean_datetime(self):
        """Ensure the event datetime is in the future."""
        datetime = self.cleaned_data.get("datetime")
        if datetime and datetime < timezone.now():
            raise forms.ValidationError("Event date must be in the future.")
        return datetime

    def clean_artists(self):
        """Ensure at least one artist is provided."""
        artists = self.cleaned_data.get("artists", "").strip()
        if not artists:
            raise forms.ValidationError("Please list at least one performing artist.")
        return artists

    def save(self, commit=True, submitter_ip=None):
        """
        Save the event with pending status and optional submitter IP.
        """
        instance = super().save(commit=False)
        instance.status = EventStatus.PENDING
        instance.source = "user submission"
        if submitter_ip:
            instance.submitter_ip = submitter_ip

        if commit:
            instance.save()
            self.save_m2m()

        return instance