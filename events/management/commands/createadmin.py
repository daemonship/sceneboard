"""
Management command to create admin users for moderation.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create an admin user for the moderation queue"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            help="Username for the admin user",
        )
        parser.add_argument(
            "--email",
            type=str,
            help="Email address for the admin user",
        )
        parser.add_argument(
            "--password",
            type=str,
            help="Password for the admin user",
        )

    def handle(self, *args, **options):
        User = get_user_model()

        username = options.get("username")
        email = options.get("email")
        password = options.get("password")

        # Interactive mode if no arguments provided
        if not username:
            username = input("Enter username: ")
        if not email:
            email = input("Enter email: ")
        if not password:
            password = input("Enter password: ")

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            # Update existing user to be admin
            user = User.objects.get(username=username)
            user.is_staff = True
            user.is_superuser = True
            user.email = email
            user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Updated existing user "{username}" to admin')
            )
        else:
            # Create new admin user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_staff=True,
                is_superuser=True,
            )
            self.stdout.write(self.style.SUCCESS(f'Created admin user "{username}"'))

        self.stdout.write(
            self.style.WARNING("Admin users can access the moderation queue at /admin/")
        )
