from django.urls import path

from . import views

urlpatterns = [
    path("", views.event_feed, name="event_feed"),
    path("events/<slug:slug>/", views.event_detail, name="event_detail"),
]
