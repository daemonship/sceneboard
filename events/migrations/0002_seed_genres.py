"""
Seed data migration for Genre tags.
"""

from django.db import migrations


def seed_genres(apps, schema_editor):
    """Seed initial genre tags."""
    Genre = apps.get_model("events", "Genre")

    genres = [
        # Rock variants
        "Rock",
        "Punk",
        "Metal",
        "Hardcore",
        "Indie Rock",
        "Alternative Rock",
        "Post-Rock",
        "Psychedelic Rock",
        # Electronic
        "Electronic",
        "House",
        "Techno",
        "EDM",
        "Synthwave",
        "Ambient",
        # Hip Hop
        "Hip Hop",
        "Rap",
        "Trap",
        # Jazz & Blues
        "Jazz",
        "Blues",
        # Folk & Acoustic
        "Folk",
        "Acoustic",
        "Americana",
        "Country",
        # Other
        "Pop",
        "R&B",
        "Soul",
        "Funk",
        "Reggae",
        "Ska",
        "Experimental",
        "Noise",
    ]

    for name in genres:
        Genre.objects.get_or_create(
            name=name,
            defaults={"slug": name.lower().replace(" ", "-").replace("&", "")},
        )


def reverse_seed(apps, schema_editor):
    """Remove seeded genres."""
    Genre = apps.get_model("events", "Genre")
    Genre.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_genres, reverse_seed),
    ]
