from django.contrib import admin
from django.utils.html import format_html

from .models import Event, EventStatus, Genre, Venue


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ["name", "address", "ical_feed_url", "last_polled", "created_at"]
    search_fields = ["name", "address"]
    readonly_fields = ["last_polled", "created_at"]
    fieldsets = (
        (None, {"fields": ("name", "address")}),
        ("iCal Integration", {"fields": ("ical_feed_url", "last_polled")}),
    )


class GenreInline(admin.TabularInline):
    model = Event.genre_tags.through
    extra = 1
    verbose_name = "Genre Tag"
    verbose_name_plural = "Genre Tags"


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["name", "datetime", "venue", "status_badge", "source", "created_at"]
    list_filter = ["status", "datetime", "genre_tags", "venue"]
    search_fields = ["name", "artists", "notes", "venue__name"]
    readonly_fields = ["slug", "submitter_ip", "created_at", "updated_at"]
    inlines = [GenreInline]

    # Date hierarchy for easy browsing
    date_hierarchy = "datetime"

    # Default ordering
    ordering = ["-datetime"]

    # Custom actions
    actions = ["approve_events", "reject_events"]

    fieldsets = (
        (None, {"fields": ("name", "slug", "datetime", "venue")}),
        ("Event Details", {"fields": ("artists", "genre_tags", "link", "notes")}),
        ("Status & Source", {"fields": ("status", "source")}),
        (
            "Metadata",
            {
                "fields": ("submitter_ip", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def status_badge(self, obj):
        """Display status as a colored badge."""
        colors = {
            "pending": "#ffc107",  # yellow/warning
            "approved": "#28a745",  # green/success
            "rejected": "#dc3545",  # red/danger
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"

    def approve_events(self, request, queryset):
        """Bulk action to approve events.

        Note: uses queryset.update() which bypasses model save() and signals.
        If approval side effects are ever added to save(), switch to per-object iteration.
        """
        updated = queryset.update(status=EventStatus.APPROVED)
        self.message_user(request, f"{updated} event(s) approved.")

    approve_events.short_description = "Approve selected events"

    def reject_events(self, request, queryset):
        """Bulk action to reject events.

        Note: uses queryset.update() which bypasses model save() and signals.
        If rejection side effects are ever added to save(), switch to per-object iteration.
        """
        updated = queryset.update(status=EventStatus.REJECTED)
        self.message_user(request, f"{updated} event(s) rejected.")

    reject_events.short_description = "Reject selected events"
