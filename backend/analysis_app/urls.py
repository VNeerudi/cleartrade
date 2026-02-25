from django.urls import path
from .views import analyze, history, chat

urlpatterns = [
    path("analyze", analyze),
    path("history", history),
    path("chat", chat),
]