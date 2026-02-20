# SceneBoard - Local Music Scene Tracker

> Discover local music events in your city. Filter by genre, date, and venue.

## What It Solves

Fans of niche local music genres can see all upcoming shows in their city in one place and submit shows they know about.

## MVP Scope

### The One Thing
Let fans discover all upcoming local music events in one place with easy filtering and submission.

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

# Run migrations
python manage.py migrate

# Create admin user (optional, for testing)
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

Visit http://localhost:8000 to see the site.

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=.

# Run specific test file
pytest tests.py
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

## Development Tasks

| Task | Status | Description |
|------|--------|-------------|
| Task 1 | ✅ Complete | Initialize Django project skeleton |
| Task 2 | ⏳ Pending | Event models, admin auth, and moderation queue |
| Task 3 | ⏳ Pending | Event feed page with genre and date filtering |
| Task 4 | ⏳ Pending | Event detail page and submission form |
| Task 5 | ⏳ Pending | iCal feed ingestion worker |
| Task 6 | ⏳ Pending | Code review |
| Task 7 | ⏳ Pending | Pre-launch verification |
| Task 8 | ⏳ Pending | Deploy to production |

## License

MIT

---

*Built by [DaemonShip](https://github.com/daemonship) — autonomous venture studio*
