from django.db import models

class StockPrice(models.Model):
    ticker = models.CharField(max_length=32, db_index=True)
    date = models.DateField(db_index=True)
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.BigIntegerField()

    class Meta:
        unique_together = ("ticker", "date")
        ordering = ["date"]

class FundamentalMetric(models.Model):
    ticker = models.CharField(max_length=64, db_index=True)
    period_end = models.DateField(db_index=True)
    pe_ratio = models.FloatField(null=True, blank=True)
    earnings_growth = models.FloatField(null=True, blank=True)
    revenue_growth = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["-period_end"]

class NewsHeadline(models.Model):
    ticker = models.CharField(max_length=64, db_index=True)
    date = models.DateField(db_index=True)
    headline = models.TextField()

    class Meta:
        ordering = ["-date"]

class Recommendation(models.Model):
    ticker = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    signal = models.CharField(max_length=8)  # BUY/HOLD/SELL
    confidence = models.FloatField()
    explanation = models.TextField()

    ma_10 = models.FloatField(null=True, blank=True)
    ma_30 = models.FloatField(null=True, blank=True)
    rsi = models.FloatField(null=True, blank=True)
    volatility = models.FloatField(null=True, blank=True)
    sentiment = models.FloatField(null=True, blank=True)

    pe_ratio = models.FloatField(null=True, blank=True)
    earnings_growth = models.FloatField(null=True, blank=True)
    revenue_growth = models.FloatField(null=True, blank=True)