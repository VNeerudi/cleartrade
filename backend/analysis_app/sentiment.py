def score_sentiment(headlines: list[str]) -> float:
    if not headlines:
        return 0.0

    pos = {"gain","gains","up","rise","rises","surge","strong","record","profit","growth","bullish","upgrade"}
    neg = {"down","drop","drops","fall","falls","plunge","weak","loss","decline","bearish","downgrade","lawsuit"}

    scores = []
    for h in headlines:
        tokens = [t.strip(".,:;!?()[]{}\"'").lower() for t in str(h).split()]
        p = sum(1 for t in tokens if t in pos)
        n = sum(1 for t in tokens if t in neg)
        scores.append((p - n) / max(1, (p + n)))
    return float(sum(scores) / len(scores))