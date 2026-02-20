"""Tests for SceneBoard Django project."""
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
