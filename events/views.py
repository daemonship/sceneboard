from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Event, EventStatus, Genre


def _get_date_bounds(date_range):
    """Return (start, end) datetime bounds for a named date preset."""
    now = timezone.localtime(timezone.now())
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if date_range == "tonight":
        end = today_start.replace(hour=23, minute=59, second=59)
        return today_start, end

    if date_range == "this-week":
        # Monday through Sunday of the current calendar week
        days_to_monday = now.weekday()
        week_start = today_start - timezone.timedelta(days=days_to_monday)
        week_end = week_start + timezone.timedelta(
            days=6, hours=23, minutes=59, seconds=59
        )
        return week_start, week_end

    if date_range == "this-weekend":
        # Saturday and Sunday of the current calendar week
        days_to_saturday = (5 - now.weekday()) % 7
        sat_start = today_start + timezone.timedelta(days=days_to_saturday)
        sun_end = sat_start + timezone.timedelta(
            days=1, hours=23, minutes=59, seconds=59
        )
        return sat_start, sun_end

    return None, None


def event_feed(request):
    """Main public event feed — upcoming approved events with genre/date filters."""
    all_genres = Genre.objects.all()

    # Parse genre filter: ?genres=rock&genres=jazz
    selected_genres = request.GET.getlist("genres")

    # Parse date range preset: ?date_range=tonight|this-week|this-weekend
    date_range = request.GET.get("date_range", "")

    now = timezone.now()
    qs = (
        Event.objects.filter(status=EventStatus.APPROVED, datetime__gte=now)
        .select_related("venue")
        .prefetch_related("genre_tags")
        .order_by("datetime")
    )

    if selected_genres:
        qs = qs.filter(genre_tags__slug__in=selected_genres).distinct()

    if date_range:
        start, end = _get_date_bounds(date_range)
        if start and end:
            qs = qs.filter(datetime__gte=start, datetime__lte=end)

    events = list(qs)

    is_partial = request.GET.get("partial") == "1"

    context = {
        "events": events,
        "all_genres": all_genres,
        "selected_genres": selected_genres,
        "date_range": date_range,
        "DATE_PRESETS": [
            ("tonight", "Tonight"),
            ("this-week", "This Week"),
            ("this-weekend", "This Weekend"),
        ],
    }

    if is_partial:
        return render(request, "events/partials/event_list.html", context)

    return render(request, "events/feed.html", context)


def event_detail(request, slug):
    """Public detail page for a single event."""
    event = get_object_or_404(Event, slug=slug, status=EventStatus.APPROVED)
    return render(request, "events/detail.html", {"event": event})
