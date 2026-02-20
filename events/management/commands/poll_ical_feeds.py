"""
Management command to poll venue iCal feeds and import upcoming events.

Designed to run every 6 hours via Fly.io scheduled machines:
    fly machine run --app sceneboard --schedule 6h -- python manage.py poll_ical_feeds
"""

import logging
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime
from datetime import timezone as dt_timezone

from django.core.management.base import BaseCommand
from django.utils import timezone
from icalendar import Calendar

from events.models import Event, EventStatus, Venue

logger = logging.getLogger(__name__)

FETCH_TIMEOUT = 15  # seconds
USER_AGENT = "SceneBoard/1.0 iCal-Importer"


def normalize_name(name: str) -> str:
    """Normalize event name for deduplication: lowercase, NFKD, collapse whitespace."""
    name = unicodedata.normalize("NFKD", name).lower().strip()
    return " ".join(name.split())


class Command(BaseCommand):
    help = "Poll venue iCal feeds and import upcoming events (designed for 6-hour cron)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--venue-id",
            type=int,
            help="Poll only this venue (by ID); defaults to all venues with feeds",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse feeds and report results without writing to the database",
        )

    def handle(self, *args, **options):
        venue_id = options.get("venue_id")
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no database writes"))

        qs = Venue.objects.exclude(ical_feed_url="")
        if venue_id:
            qs = qs.filter(pk=venue_id)

        venues = list(qs)
        if not venues:
            self.stdout.write("No venues with iCal feeds found.")
            return

        total_created = 0
        total_skipped = 0
        error_count = 0

        for venue in venues:
            self.stdout.write(f"Polling: {venue.name}")
            try:
                created, skipped = self._poll_venue(venue, dry_run)
                total_created += created
                total_skipped += skipped
                self.stdout.write(f"  {created} created, {skipped} skipped")
            except Exception as exc:
                error_count += 1
                logger.error(
                    "Feed error for venue '%s' (%s): %s",
                    venue.name,
                    venue.ical_feed_url,
                    exc,
                    exc_info=True,
                )
                self.stderr.write(
                    self.style.ERROR(f"  Feed error for {venue.name}: {exc}")
                )

        summary = (
            f"Poll complete — {total_created} created, "
            f"{total_skipped} duplicates/past, "
            f"{error_count} feed errors"
        )
        self.stdout.write(self.style.SUCCESS(summary))

    def _poll_venue(self, venue: Venue, dry_run: bool) -> tuple[int, int]:
        """
        Fetch, parse, and import events from one venue's iCal feed.

        Returns (created_count, skipped_count).
        Raises on network or parse failure — caller handles per-feed errors.
        """
        raw = self._fetch_feed(venue.ical_feed_url)
        cal = Calendar.from_ical(raw)

        now = timezone.now()
        cutoff = now - timezone.timedelta(hours=1)  # allow slightly-past events

        created = 0
        skipped = 0

        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            summary = str(component.get("SUMMARY", "")).strip()
            if not summary:
                continue

            event_dt = self._parse_dtstart(component)
            if event_dt is None or event_dt < cutoff:
                skipped += 1
                continue

            if self._is_duplicate(venue, event_dt, summary):
                skipped += 1
                continue

            if not dry_run:
                self._create_event(venue, summary, event_dt, component)
            else:
                self.stdout.write(f"  [dry-run] {summary} on {event_dt.date()}")

            created += 1

        if not dry_run:
            venue.last_polled = now
            venue.save(update_fields=["last_polled"])

        return created, skipped

    def _fetch_feed(self, url: str) -> bytes:
        """Fetch iCal feed URL, returning raw bytes."""
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            return resp.read()

    def _parse_dtstart(self, component) -> datetime | None:
        """
        Parse DTSTART from an iCal VEVENT.

        Handles both datetime and date-only values. Always returns a UTC-aware
        datetime, or None if the field is absent or unparseable.
        """
        dtstart = component.get("DTSTART")
        if dtstart is None:
            return None
        try:
            val = dtstart.dt
            if isinstance(val, datetime):
                if val.tzinfo is None:
                    return val.replace(tzinfo=dt_timezone.utc)
                return val.astimezone(dt_timezone.utc)
            else:
                # date-only — treat as midnight UTC
                return datetime(val.year, val.month, val.day, tzinfo=dt_timezone.utc)
        except Exception as exc:
            logger.warning(
                "DTSTART parse failed for VEVENT SUMMARY=%r (dtstart=%r): %s",
                component.get("SUMMARY", "<no summary>"),
                dtstart,
                exc,
            )
            return None

    def _is_duplicate(self, venue: Venue, event_dt: datetime, name: str) -> bool:
        """
        Return True if an event with the same normalized name and date already
        exists for this venue.
        """
        same_date_names = Event.objects.filter(
            venue=venue,
            datetime__date=event_dt.date(),
        ).values_list("name", flat=True)

        norm = normalize_name(name)
        return any(normalize_name(n) == norm for n in same_date_names)

    def _create_event(
        self, venue: Venue, summary: str, event_dt: datetime, component
    ) -> Event:
        """Create and return an auto-approved Event from an iCal VEVENT."""
        description = str(component.get("DESCRIPTION", "")).strip()
        url = str(component.get("URL", "")).strip()
        if not url.startswith(("http://", "https://")):
            url = ""

        return Event.objects.create(
            name=summary,
            datetime=event_dt,
            venue=venue,
            # iCal has no structured artists field; use summary as best-effort value
            artists=summary,
            status=EventStatus.APPROVED,
            source=f"iCal: {venue.name}",
            notes=description,
            link=url,
        )
