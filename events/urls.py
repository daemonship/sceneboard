from django.urls import path

from . import views

urlpatterns = [
    path("", views.event_feed, name="event_feed"),
    path("events/submit/", views.event_submit, name="event_submit"),
    path("submit/", views.event_submit, name="event_submit_alt"),  # Alternative URL
    path("events/<slug:slug>/", views.event_detail, name="event_detail"),
]
