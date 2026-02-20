# SceneBoard - Local Music Scene Tracker

> Discover local music events in your city. Filter by genre, date, and venue.

## Feedback & Ideas

> **This project is being built in public and we want to hear from you.**
> Found a bug? Have a feature idea? Something feel wrong or missing?
> **[Open an issue](../../issues)** — every piece of feedback directly shapes what gets built next.

## Status

> 🚧 In active development — not yet production ready

| Feature | Status | Notes |
|---------|--------|-------|
| Project scaffold & CI | ✅ Complete | Django 4.2, PostgreSQL, Fly.io, GitHub Actions |
| Event models & admin moderation | ✅ Complete | Genre/Venue/Event models, rate limiting, approve/reject queue |
| Event feed with filtering | ✅ Complete | Genre multi-select, date presets, no-reload updates |
| Event detail page & submission form | ✅ Complete | OG tags, Google Maps links, share buttons, anonymous submission |
| iCal feed ingestion worker | 📋 Planned | |
| Code review | 📋 Planned | |
| Pre-launch verification | 📋 Planned | |
| Deploy to production | 📋 Planned | |

## What It Solves

Fans of niche local music genres can see all upcoming shows in their city in one place and submit shows they know about.

## MVP Scope

### Included in MVP

1. **Event feed with genre + date filtering** — chronological list, filter by genre tags and date range (tonight / this week / this weekend)
2. **Event detail pages** — full event info with venue details and social sharing
3. **Anonymous event submission** — anyone can submit a show for moderation
4. **Admin moderation queue** — approve/reject submitted events
5. **iCal feed ingestion** — automatically import events from venue calendars

## Tech Stack

- **Backend:** Django 4.2 with PostgreSQL
- **Frontend:** Django templates with vanilla JavaScript
- **Deployment:** Fly.io (Docker)
- **CI:** GitHub Actions (linting, tests)

## Development Setup

### Prerequisites
- Python 3.10+
- PostgreSQL 15+
- Virtual environment (recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/daemonship/sceneboard.git
cd sceneboard

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env

# Edit .env and set your SECRET_KEY and database credentials

# Run migrations (also seeds ~30 genre tags)
python manage.py migrate

# Create admin user
python manage.py createadmin

# Run development server
python manage.py runserver
```

Visit http://localhost:8000 to see the event feed.
Visit http://localhost:8000/admin/ to access the moderation queue.

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=.
```

### Code Quality

```bash
# Format code
black .
isort .

# Check linting
flake8 .
```

## Deployment to Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login to Fly.io
flyctl auth login

# Deploy
flyctl deploy
```

## License

MIT

---

*Built by [DaemonShip](https://github.com/daemonship) — autonomous venture studio*
