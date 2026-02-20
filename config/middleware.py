"""
IP-based rate limiting middleware for event submissions.
Limits submissions to a configurable number per day per IP address.
"""

import logging

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseForbidden

logger = logging.getLogger(__name__)


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

                if not self.is_allowed(client_ip, request):
                    return HttpResponseForbidden(
                        content=(
                            f"<!DOCTYPE html>"
                            f"<html><head><title>Rate Limited</title></head>"
                            f"<body style=\"font-family: system-ui; padding: 40px; text-align: center;\">"
                            f"<h1>Too Many Submissions</h1>"
                            f"<p>You have exceeded the maximum number of event submissions"
                            f" ({self.max_submissions} per day).</p>"
                            f"<p>Please try again tomorrow.</p>"
                            f"</body></html>"
                        ).encode(),
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

    def is_allowed(self, ip_address, request=None):
        """
        Check if the IP address is allowed to submit based on rate limits.
        Returns True if allowed, False if rate limited.
        """
        if not ip_address:
            logger.warning(
                "SubmissionRateLimiter: could not determine client IP for %s %s; "
                "rate limiting bypassed. Check proxy configuration.",
                request.method if request else "UNKNOWN",
                request.path if request else "UNKNOWN",
            )
            return True

        cache_key = f"rate_limit:submit:{ip_address}"

        # Get current count from cache
        current_count = cache.get(cache_key, 0)

        if current_count >= self.max_submissions:
            return False

        # Increment counter atomically where possible.
        # Note: LocMemCache is per-process; use Redis in multi-worker production.
        try:
            cache.incr(cache_key)
        except ValueError:
            # Key doesn't exist yet — initialize it with the TTL
            try:
                cache.set(cache_key, 1, self.TIMEOUT_SECONDS)
            except Exception as exc:
                logger.error(
                    "SubmissionRateLimiter: cache.set() failed for IP %s: %s",
                    ip_address,
                    exc,
                    exc_info=True,
                )
        except Exception as exc:
            logger.error(
                "SubmissionRateLimiter: cache.incr() failed for IP %s: %s",
                ip_address,
                exc,
                exc_info=True,
            )

        return True
