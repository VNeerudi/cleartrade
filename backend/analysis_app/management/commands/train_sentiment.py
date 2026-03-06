from django.core.management.base import BaseCommand
from core.models import NewsHeadline
from analysis_app.sentiment_model import train_sentiment_model


class Command(BaseCommand):
    help = "Train TF-IDF + Logistic Regression sentiment model on headlines in DB (weak labels from keywords)"

    def handle(self, *args, **opts):
        headlines = list(
            NewsHeadline.objects.values_list("headline", flat=True).distinct()[:5000]
        )
        if len(headlines) < 50:
            self.stdout.write(
                self.style.WARNING("Need at least 50 headlines. Import news first (import_news_events).")
            )
            return
        train_sentiment_model(headlines, labels=None)
        self.stdout.write(self.style.SUCCESS(f"Trained sentiment model on {len(headlines)} headlines."))
