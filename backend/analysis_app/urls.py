from django.urls import path
from .views import analyze, history, chat, series

urlpatterns = [
    path("analyze", analyze),
    path("series", series),
    path("history", history),
    path("chat", chat),
]