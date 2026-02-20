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
