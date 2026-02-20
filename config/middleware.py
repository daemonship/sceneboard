"""
IP-based rate limiting middleware for event submissions.
Limits submissions to 20 per day per IP address.
"""

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseForbidden


class SubmissionRateLimiter:
    """
    Rate limiting middleware that limits submissions to a configurable
    number per IP address within a time window.
    """

    # Default: 20 submissions per day
    MAX_SUBMISSIONS = 20
    TIMEOUT_SECONDS = 86400  # 24 hours

    def __init__(self, get_response):
        self.get_response = get_response
        self.max_submissions = getattr(
            settings, "RATE_LIMIT_SUBMISSIONS", self.MAX_SUBMISSIONS
        )

    def __call__(self, request):
        # Only apply rate limiting to event submission URLs
        submission_urls = [
            "/events/submit/",
            "/submit/",
        ]

        if any(request.path.startswith(url) for url in submission_urls):
            # Only limit POST requests (actual submissions)
            if request.method == "POST":
                client_ip = self.get_client_ip(request)

                if not self.is_allowed(client_ip):
                    return HttpResponseForbidden(
                        content=b"""<!DOCTYPE html>
<html><head><title>Rate Limited</title></head>
<body style="font-family: system-ui; padding: 40px; text-align: center;">
<h1>Too Many Submissions</h1>
<p>You have exceeded the maximum number of event submissions (20 per day).</p>
<p>Please try again tomorrow.</p>
</body></html>""",
                        content_type="text/html",
                    )

        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        """
        Get the client's IP address, handling proxies and load balancers.
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            # Take the first IP in the chain (client IP)
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def is_allowed(self, ip_address):
        """
        Check if the IP address is allowed to submit based on rate limits.
        Returns True if allowed, False if rate limited.
        """
        if not ip_address:
            # No IP found - allow but log (could also block)
            return True

        cache_key = f"rate_limit:submit:{ip_address}"

        # Get current count from cache
        current_count = cache.get(cache_key, 0)

        if current_count >= self.max_submissions:
            return False

        # Increment counter
        # Use cache.add to only set if not exists, then increment
        # This is a simple approach - in production you might use Redis atomic ops
        try:
            # Try to increment atomically
            cache.incr(cache_key)
        except ValueError:
            # Key doesn't exist - set it with the timeout
            cache.set(cache_key, 1, self.TIMEOUT_SECONDS)

        return True
