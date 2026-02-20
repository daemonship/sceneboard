"""Tests for SceneBoard Django project."""
import urllib.error
from datetime import timezone as dt_timezone
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from events.models import Event, EventStatus, Genre, Venue


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def venue(db):
    return Venue.objects.create(name="The Fillmore", address="1805 Geary Blvd")


@pytest.fixture
def genre_rock(db):
    genre, _ = Genre.objects.get_or_create(name="Rock", defaults={"slug": "rock"})
    return genre


@pytest.fixture
def genre_jazz(db):
    genre, _ = Genre.objects.get_or_create(name="Jazz", defaults={"slug": "jazz"})
    return genre


@pytest.fixture
def approved_event(db, venue, genre_rock):
    event = Event.objects.create(
        name="Rock Night",
        datetime=timezone.now() + timezone.timedelta(days=1),
        venue=venue,
        artists="The Strokes\nInterpolate",
        status=EventStatus.APPROVED,
        source="user submission",
    )
    event.genre_tags.add(genre_rock)
    return event


@pytest.fixture
def pending_event(db, venue):
    return Event.objects.create(
        name="Pending Show",
        datetime=timezone.now() + timezone.timedelta(days=2),
        venue=venue,
        artists="Unknown Band",
        status=EventStatus.PENDING,
    )


@pytest.fixture
def past_event(db, venue, genre_rock):
    event = Event.objects.create(
        name="Last Week's Show",
        datetime=timezone.now() - timezone.timedelta(days=3),
        venue=venue,
        artists="Old Band",
        status=EventStatus.APPROVED,
    )
    event.genre_tags.add(genre_rock)
    return event


# ── Scaffold sanity tests ────────────────────────────────────────────────────


@pytest.mark.django_db
def test_home_page_loads(client):
    """Feed page loads at the root URL."""
    url = reverse("event_feed")
    response = client.get(url)
    assert response.status_code == 200
    assert b"SceneBoard" in response.content


@pytest.mark.django_db
def test_admin_page_requires_auth(client):
    """Admin page redirects unauthenticated users."""
    response = client.get("/admin/")
    assert response.status_code == 302


# ── Feed view tests ──────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_feed_shows_approved_events(client, approved_event):
    """Approved upcoming events appear in the feed."""
    response = client.get(reverse("event_feed"))
    assert response.status_code == 200
    assert b"Rock Night" in response.content


@pytest.mark.django_db
def test_feed_hides_pending_events(client, pending_event):
    """Pending events do not appear in the public feed."""
    response = client.get(reverse("event_feed"))
    assert b"Pending Show" not in response.content


@pytest.mark.django_db
def test_feed_hides_past_events(client, past_event):
    """Past events (even if approved) do not appear in the feed."""
    response = client.get(reverse("event_feed"))
    assert b"Last Week" not in response.content


@pytest.mark.django_db
def test_feed_genre_filter(client, approved_event, venue, genre_jazz):
    """Genre filter restricts results to matching events."""
    jazz_event = Event.objects.create(
        name="Jazz Night",
        datetime=timezone.now() + timezone.timedelta(days=3),
        venue=venue,
        artists="Miles Davis Tribute",
        status=EventStatus.APPROVED,
    )
    jazz_event.genre_tags.add(genre_jazz)

    response = client.get(reverse("event_feed") + "?genres=jazz")
    assert b"Jazz Night" in response.content
    assert b"Rock Night" not in response.content


@pytest.mark.django_db
def test_feed_multi_genre_filter(client, approved_event, venue, genre_jazz):
    """Multiple genres are OR'd together — events matching any selected genre appear."""
    jazz_event = Event.objects.create(
        name="Jazz Night",
        datetime=timezone.now() + timezone.timedelta(days=3),
        venue=venue,
        artists="Miles Davis Tribute",
        status=EventStatus.APPROVED,
    )
    jazz_event.genre_tags.add(genre_jazz)

    response = client.get(reverse("event_feed") + "?genres=rock&genres=jazz")
    assert b"Rock Night" in response.content
    assert b"Jazz Night" in response.content


@pytest.mark.django_db
def test_feed_date_range_tonight(client, approved_event, venue, genre_rock):
    """'tonight' preset filters to events happening today."""
    # approved_event is tomorrow — should NOT appear
    response = client.get(reverse("event_feed") + "?date_range=tonight")
    assert b"Rock Night" not in response.content


@pytest.mark.django_db
def test_feed_date_range_this_week(client, approved_event):
    """'this-week' preset returns events within the current calendar week."""
    # approved_event is tomorrow — should appear if still within this week
    response = client.get(reverse("event_feed") + "?date_range=this-week")
    assert response.status_code == 200  # just ensure no server error


@pytest.mark.django_db
def test_feed_partial_response(client, approved_event):
    """?partial=1 returns only the event list fragment, not the full page."""
    response = client.get(reverse("event_feed") + "?partial=1")
    assert response.status_code == 200
    # Partial should contain the event grid, not the full HTML shell
    assert b"<!DOCTYPE html>" not in response.content
    assert b"event-card" in response.content or b"events-empty" in response.content


@pytest.mark.django_db
def test_feed_empty_state(client):
    """When no events match, the empty state is rendered."""
    response = client.get(reverse("event_feed"))
    assert b"events-empty" in response.content or b"No shows found" in response.content


@pytest.mark.django_db
def test_feed_shows_genre_chips(client, approved_event):
    """Approved events with genre tags display genre chips."""
    response = client.get(reverse("event_feed"))
    assert b"genre-chip" in response.content
    assert b"Rock" in response.content


@pytest.mark.django_db
def test_feed_shows_source_attribution(client, approved_event):
    """Events with a source field show source attribution."""
    response = client.get(reverse("event_feed"))
    assert b"user submission" in response.content


@pytest.mark.django_db
def test_feed_events_sorted_by_date(client, venue, genre_rock):
    """Events are returned in ascending datetime order."""
    Event.objects.create(
        name="Later Show",
        datetime=timezone.now() + timezone.timedelta(days=5),
        venue=venue,
        artists="Band B",
        status=EventStatus.APPROVED,
    )
    Event.objects.create(
        name="Sooner Show",
        datetime=timezone.now() + timezone.timedelta(days=2),
        venue=venue,
        artists="Band A",
        status=EventStatus.APPROVED,
    )

    response = client.get(reverse("event_feed"))
    content = response.content.decode()
    assert content.index("Sooner Show") < content.index("Later Show")


# ── Event Detail Page Tests ─────────────────────────────────────────────────


@pytest.mark.django_db
def test_event_detail_page_loads(client, approved_event):
    """Event detail page loads and shows event information."""
    url = reverse("event_detail", kwargs={"slug": approved_event.slug})
    response = client.get(url)
    assert response.status_code == 200
    assert b"Rock Night" in response.content
    assert b"The Fillmore" in response.content
    assert b"The Strokes" in response.content


@pytest.mark.django_db
def test_event_detail_has_og_tags(client, approved_event):
    """Event detail page includes Open Graph meta tags."""
    url = reverse("event_detail", kwargs={"slug": approved_event.slug})
    response = client.get(url)
    assert response.status_code == 200
    content = response.content.decode()
    assert 'property="og:title"' in content
    assert 'property="og:description"' in content
    assert 'property="og:type"' in content
    assert 'property="og:url"' in content


@pytest.mark.django_db
def test_event_detail_has_google_maps_link(client, approved_event):
    """Event detail page includes Google Maps link for venue."""
    url = reverse("event_detail", kwargs={"slug": approved_event.slug})
    response = client.get(url)
    assert response.status_code == 200
    content = response.content.decode()
    assert "google.com/maps" in content


@pytest.mark.django_db
def test_event_detail_hides_pending_events(client, pending_event):
    """Pending events return 404 on detail page."""
    url = reverse("event_detail", kwargs={"slug": pending_event.slug})
    response = client.get(url)
    assert response.status_code == 404


# ── Event Submission Form Tests ─────────────────────────────────────────────


@pytest.mark.django_db
def test_submission_form_page_loads(client):
    """Submission form page loads successfully."""
    url = reverse("event_submit")
    response = client.get(url)
    assert response.status_code == 200
    assert b"Submit" in response.content


@pytest.mark.django_db
def test_submission_form_creates_pending_event(client, venue, genre_rock):
    """Submitting the form creates a pending event."""
    url = reverse("event_submit")
    future_datetime = timezone.now() + timezone.timedelta(days=7)
    
    data = {
        "name": "Test Show Submission",
        "datetime": future_datetime.strftime("%Y-%m-%dT%H:%M"),
        "venue": venue.id,
        "artists": "Test Band\nAnother Band",
        "genre_tags": [genre_rock.id],
        "link": "https://example.com/event",
        "notes": "Test notes",
    }
    
    response = client.post(url, data)
    
    # Should redirect to feed after successful submission
    assert response.status_code == 302
    assert response.url == reverse("event_feed")
    
    # Event should be created with pending status
    event = Event.objects.get(name="Test Show Submission")
    assert event.status == EventStatus.PENDING
    assert event.source == "user submission"
    assert event.artists == "Test Band\nAnother Band"


@pytest.mark.django_db
def test_submission_form_validates_future_date(client, venue):
    """Submission form rejects past dates."""
    url = reverse("event_submit")
    past_datetime = timezone.now() - timezone.timedelta(days=1)
    
    data = {
        "name": "Past Show",
        "datetime": past_datetime.strftime("%Y-%m-%dT%H:%M"),
        "venue": venue.id,
        "artists": "Some Band",
    }
    
    response = client.post(url, data)
    
    # Should not redirect, should show form with errors
    assert response.status_code == 200
    assert b"future" in response.content.lower() or b"error" in response.content.lower()
    
    # Event should not be created
    assert not Event.objects.filter(name="Past Show").exists()


@pytest.mark.django_db
def test_submission_form_requires_artists(client, venue):
    """Submission form requires at least one artist."""
    url = reverse("event_submit")
    future_datetime = timezone.now() + timezone.timedelta(days=7)
    
    data = {
        "name": "No Artists Show",
        "datetime": future_datetime.strftime("%Y-%m-%dT%H:%M"),
        "venue": venue.id,
        "artists": "",  # Empty artists
    }
    
    response = client.post(url, data)
    
    # Should not redirect
    assert response.status_code == 200
    
    # Event should not be created
    assert not Event.objects.filter(name="No Artists Show").exists()


@pytest.mark.django_db
def test_submission_form_stores_submitter_ip(client, venue):
    """Submission form stores the submitter's IP address."""
    url = reverse("event_submit")
    future_datetime = timezone.now() + timezone.timedelta(days=7)
    
    data = {
        "name": "IP Test Show",
        "datetime": future_datetime.strftime("%Y-%m-%dT%H:%M"),
        "venue": venue.id,
        "artists": "Test Band",
    }
    
    response = client.post(url, data, REMOTE_ADDR="192.168.1.100")
    
    event = Event.objects.get(name="IP Test Show")
    assert event.submitter_ip == "192.168.1.100"


@pytest.mark.django_db
def test_submission_form_optional_fields(client, venue):
    """Submission form works with only required fields."""
    url = reverse("event_submit")
    future_datetime = timezone.now() + timezone.timedelta(days=7)
    
    data = {
        "name": "Minimal Show",
        "datetime": future_datetime.strftime("%Y-%m-%dT%H:%M"),
        "venue": venue.id,
        "artists": "Solo Artist",
        # No link, notes, or genre_tags
    }
    
    response = client.post(url, data)
    
    # Should redirect to feed
    assert response.status_code == 302
    
    # Event should be created
    event = Event.objects.get(name="Minimal Show")
    assert event.status == EventStatus.PENDING
    assert event.link == ""
    assert event.notes == ""
    assert list(event.genre_tags.all()) == []


@pytest.mark.django_db
def test_submission_form_redirects_after_success(client, venue):
    """Successful submission redirects to the feed page."""
    url = reverse("event_submit")
    future_datetime = timezone.now() + timezone.timedelta(days=7)
    
    data = {
        "name": "Success Redirect Show",
        "datetime": future_datetime.strftime("%Y-%m-%dT%H:%M"),
        "venue": venue.id,
        "artists": "Test Band",
    }
    
    response = client.post(url, data)
    
    # Should redirect to feed page
    assert response.status_code == 302
    assert response.url == reverse("event_feed")
    
    # Event should be created with pending status
    event = Event.objects.get(name="Success Redirect Show")
    assert event.status == EventStatus.PENDING


# ── iCal Feed Ingestion Tests ────────────────────────────────────────────────


def make_ical(events: list[dict]) -> bytes:
    """Build a minimal but valid iCal feed from a list of event dicts.

    Each dict may have: summary, dtstart (str, e.g. '20260301T200000Z'),
    description, url.
    """
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//SceneBoard Test//EN"]
    for ev in events:
        lines += [
            "BEGIN:VEVENT",
            f"SUMMARY:{ev['summary']}",
            f"DTSTART:{ev['dtstart']}",
            f"DTEND:{ev.get('dtend', ev['dtstart'])}",
        ]
        if "description" in ev:
            lines.append(f"DESCRIPTION:{ev['description']}")
        if "url" in ev:
            lines.append(f"URL:{ev['url']}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines).encode()


@pytest.fixture
def ical_venue(db):
    return Venue.objects.create(
        name="Bottom of the Hill",
        address="1233 17th St, San Francisco, CA",
        ical_feed_url="https://example.com/feed.ics",
    )


def run_command(*args, **kwargs):
    """Call the poll_ical_feeds management command and return stdout output."""
    from django.core.management import call_command

    out = StringIO()
    err = StringIO()
    call_command("poll_ical_feeds", *args, stdout=out, stderr=err, **kwargs)
    return out.getvalue(), err.getvalue()


def mock_fetch(ical_bytes):
    """Return a context manager mock that yields a response with .read()."""
    resp = MagicMock()
    resp.read.return_value = ical_bytes
    resp.__enter__ = lambda s: resp
    resp.__exit__ = MagicMock(return_value=False)
    return resp


@pytest.mark.django_db
def test_poll_creates_events(ical_venue):
    """Valid iCal feed creates auto-approved events."""
    feed = make_ical(
        [{"summary": "Night Owls", "dtstart": "20260310T200000Z"}]
    )
    with patch(
        "events.management.commands.poll_ical_feeds.urllib.request.urlopen",
        return_value=mock_fetch(feed),
    ):
        run_command()

    assert Event.objects.filter(name="Night Owls").exists()
    event = Event.objects.get(name="Night Owls")
    assert event.status == EventStatus.APPROVED
    assert event.venue == ical_venue
    assert event.source == f"iCal: {ical_venue.name}"


@pytest.mark.django_db
def test_poll_sets_last_polled(ical_venue):
    """last_polled is updated on the venue after a successful poll."""
    assert ical_venue.last_polled is None
    feed = make_ical([{"summary": "Show", "dtstart": "20260310T200000Z"}])
    with patch(
        "events.management.commands.poll_ical_feeds.urllib.request.urlopen",
        return_value=mock_fetch(feed),
    ):
        run_command()

    ical_venue.refresh_from_db()
    assert ical_venue.last_polled is not None


@pytest.mark.django_db
def test_poll_skips_past_events(ical_venue):
    """Events more than 1 hour in the past are not imported."""
    feed = make_ical([{"summary": "Old Show", "dtstart": "20200101T200000Z"}])
    with patch(
        "events.management.commands.poll_ical_feeds.urllib.request.urlopen",
        return_value=mock_fetch(feed),
    ):
        run_command()

    assert not Event.objects.filter(name="Old Show").exists()


@pytest.mark.django_db
def test_poll_deduplicates_events(ical_venue):
    """Importing the same feed twice does not create duplicate events."""
    feed = make_ical([{"summary": "Dupe Show", "dtstart": "20260315T200000Z"}])
    with patch(
        "events.management.commands.poll_ical_feeds.urllib.request.urlopen",
        return_value=mock_fetch(feed),
    ):
        run_command()
        run_command()

    assert Event.objects.filter(name="Dupe Show").count() == 1


@pytest.mark.django_db
def test_poll_deduplicates_normalized_names(ical_venue):
    """Deduplication ignores case and extra whitespace in event names."""
    feed = make_ical([{"summary": "  Night  Owls  ", "dtstart": "20260315T200000Z"}])
    # Pre-create an event with slightly different formatting
    Event.objects.create(
        name="Night Owls",
        datetime=timezone.datetime(2026, 3, 15, 20, 0, 0, tzinfo=dt_timezone.utc),
        venue=ical_venue,
        artists="Night Owls",
        status=EventStatus.APPROVED,
        source="manual",
    )

    with patch(
        "events.management.commands.poll_ical_feeds.urllib.request.urlopen",
        return_value=mock_fetch(feed),
    ):
        run_command()

    assert Event.objects.filter(venue=ical_venue).count() == 1


@pytest.mark.django_db
def test_poll_bad_feed_does_not_crash_other_venues(db):
    """A malformed feed for one venue does not stop other venues from polling."""
    bad_venue = Venue.objects.create(
        name="Bad Venue",
        ical_feed_url="https://bad.example.com/broken.ics",
    )
    good_venue = Venue.objects.create(
        name="Good Venue",
        ical_feed_url="https://good.example.com/feed.ics",
    )
    good_feed = make_ical([{"summary": "Good Show", "dtstart": "20260310T200000Z"}])

    def fake_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "bad" in url:
            raise urllib.error.URLError("connection refused")
        return mock_fetch(good_feed)

    with patch(
        "events.management.commands.poll_ical_feeds.urllib.request.urlopen",
        side_effect=fake_urlopen,
    ):
        out, err = run_command()

    assert Event.objects.filter(name="Good Show").exists()
    assert not Event.objects.filter(venue=bad_venue).exists()
    assert "Feed error" in err


@pytest.mark.django_db
def test_poll_stores_description_and_link(ical_venue):
    """DESCRIPTION and URL from iCal are stored on the created event."""
    feed = make_ical(
        [
            {
                "summary": "Described Show",
                "dtstart": "20260320T200000Z",
                "description": "Great night of music",
                "url": "https://tickets.example.com/show",
            }
        ]
    )
    with patch(
        "events.management.commands.poll_ical_feeds.urllib.request.urlopen",
        return_value=mock_fetch(feed),
    ):
        run_command()

    event = Event.objects.get(name="Described Show")
    assert event.notes == "Great night of music"
    assert event.link == "https://tickets.example.com/show"


@pytest.mark.django_db
def test_poll_handles_date_only_dtstart(ical_venue):
    """Date-only DTSTART (no time component) is imported as midnight UTC."""
    feed = make_ical([{"summary": "Date Only Show", "dtstart": "20260325"}])
    with patch(
        "events.management.commands.poll_ical_feeds.urllib.request.urlopen",
        return_value=mock_fetch(feed),
    ):
        run_command()

    assert Event.objects.filter(name="Date Only Show").exists()
    event = Event.objects.get(name="Date Only Show")
    assert event.datetime.hour == 0
    assert event.datetime.minute == 0


@pytest.mark.django_db
def test_poll_dry_run_does_not_create_events(ical_venue):
    """--dry-run reports events without writing them."""
    feed = make_ical([{"summary": "Dry Run Show", "dtstart": "20260310T200000Z"}])
    with patch(
        "events.management.commands.poll_ical_feeds.urllib.request.urlopen",
        return_value=mock_fetch(feed),
    ):
        out, _ = run_command(dry_run=True)

    assert not Event.objects.filter(name="Dry Run Show").exists()
    assert "dry-run" in out.lower()
    ical_venue.refresh_from_db()
    assert ical_venue.last_polled is None


@pytest.mark.django_db
def test_poll_skips_venues_without_feed(db):
    """Venues without an ical_feed_url are ignored."""
    Venue.objects.create(name="No Feed Venue", address="123 Main St")
    out, _ = run_command()
    assert "No venues with iCal feeds found" in out


@pytest.mark.django_db
def test_poll_venue_id_filter(db):
    """--venue-id restricts polling to a single venue."""
    venue_a = Venue.objects.create(
        name="Venue A", ical_feed_url="https://a.example.com/feed.ics"
    )
    venue_b = Venue.objects.create(
        name="Venue B", ical_feed_url="https://b.example.com/feed.ics"
    )
    feed_a = make_ical([{"summary": "Show A", "dtstart": "20260310T200000Z"}])
    feed_b = make_ical([{"summary": "Show B", "dtstart": "20260310T200000Z"}])

    def fake_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        return mock_fetch(feed_a if "a.example" in url else feed_b)

    with patch(
        "events.management.commands.poll_ical_feeds.urllib.request.urlopen",
        side_effect=fake_urlopen,
    ):
        run_command(venue_id=venue_a.pk)

    assert Event.objects.filter(name="Show A").exists()
    assert not Event.objects.filter(name="Show B").exists()
