from django.db import models
from django.utils.text import slugify


class Genre(models.Model):
    """Music genre tags for categorizing events."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Venue(models.Model):
    """Music venue with optional iCal feed for automatic event import."""

    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    ical_feed_url = models.URLField(blank=True, max_length=500)
    last_polled = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class EventStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class Event(models.Model):
    """Music event submitted by users or imported from venue iCal feeds."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True)
    datetime = models.DateTimeField()
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="events")
    artists = models.TextField(
        help_text="List of performing artists/bands, one per line"
    )
    genre_tags = models.ManyToManyField(Genre, related_name="events", blank=True)
    status = models.CharField(
        max_length=20, choices=EventStatus.choices, default=EventStatus.PENDING
    )
    source = models.CharField(
        max_length=200,
        blank=True,
        help_text="Source of the event (e.g., 'user submission', 'venue feed')",
    )
    notes = models.TextField(blank=True, help_text="Additional notes about the event")
    link = models.URLField(
        blank=True, max_length=500, help_text="Link to event details / tickets"
    )
    submitter_ip = models.GenericIPAddressField(
        null=True, blank=True, help_text="IP address of submitter (for rate limiting)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["datetime"]
        indexes = [
            models.Index(fields=["datetime"]),
            models.Index(fields=["status", "datetime"]),
        ]

    def __str__(self):
        return f"{self.name} at {self.venue.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            # Create slug from name and datetime
            date_str = self.datetime.strftime("%Y%m%d") if self.datetime else ""
            base_slug = slugify(self.name)[: 200 - len(date_str) - 1]
            self.slug = f"{base_slug}-{date_str}"

            # Ensure slug is unique
            original_slug = self.slug
            counter = 1
            while Event.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)

    def get_artists_list(self):
        """Return artists as a list (one per line)."""
        return [line.strip() for line in self.artists.split("\n") if line.strip()]

    def get_absolute_url(self):
        """Return URL for this event."""
        from django.urls import reverse

        return reverse("event_detail", kwargs={"slug": self.slug})
