"""
Django settings for SceneBoard tests.

Uses SQLite in-memory database for fast tests.
"""
from config.settings import *  # noqa

# Override database to use SQLite for tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable cache for tests (or use dummy)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}
