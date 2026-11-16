import yfinance as yf
from gnews import GNews
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import datetime
import logging
import re
from functools import lru_cache
from threading import Lock

logger = logging.getLogger(__name__)
analyzer = SentimentIntensityAnalyzer()

_finbert_pipe = None
_model_lock = Lock()


def _get_finbert():
    global _finbert_pipe
    if _finbert_pipe is None:
        try:
            from transformers import pipeline
            _finbert_pipe = pipeline(
                "text-classification",
                model="ProsusAI/finbert",
                top_k=None,
            )
        except Exception as exc:
            logger.warning("FinBERT not available, falling back to VADER: %s", exc)
            _finbert_pipe = False
    return _finbert_pipe


def _score_with_finbert(text: str) -> dict:
    """Score text with FinBERT. Returns VADER-like dict with compound/pos/neg/neu."""
    with _model_lock:
        pipe = _get_finbert()
    if pipe is False:
        return {**analyzer.polarity_scores(text), "model": "VADER"}

    try:
        # Transformers versions return either a flat list or a nested batch.
        with _model_lock:
            result = pipe(text, top_k=None, truncation=True, max_length=512)
        if isinstance(result, list) and result and isinstance(result[0], list):
            result = result[0]
        scores = {item["label"].lower(): float(item["score"]) for item in result}
        if not {"positive", "negative", "neutral"}.issubset(scores):
            raise ValueError("Incomplete FinBERT scores")
        pos, neg, neu = scores["positive"], scores["negative"], scores["neutral"]
        return {"compound": pos - neg, "pos": pos, "neg": neg, "neu": neu,
                "model": "FinBERT"}
    except Exception as exc:
        logger.warning("FinBERT inference failed; using VADER: %s", exc)
        return {**analyzer.polarity_scores(text), "model": "VADER"}


@lru_cache(maxsize=512)
def _news_identity(ticker):
    """Resolve arbitrary exchange symbols without a hard-coded company list."""
    try:
        quotes = yf.Search(ticker, max_results=5, news_count=0).quotes
        for quote in quotes:
            if str(quote.get("symbol", "")).upper() == ticker:
                return quote.get("longname") or quote.get("shortname") or ticker.split(".")[0]
    except Exception as exc:
        logger.warning("Company lookup unavailable for %s: %s", ticker, exc)
    return ticker.rsplit(".", 1)[0] if "." in ticker else ticker


# ── Yahoo Finance News ──────────────────────────────────
def _fetch_yahoo_news(ticker: str) -> list:
    """Fetch news from Yahoo Finance via yfinance."""
    try:
        stock = yf.Ticker(ticker)
        raw = stock.news or []
    except Exception:
        return []

    articles = []
    for item in raw[:10]:
        content = item.get("content") or item
        if not isinstance(content, dict):
            continue
        title = content.get("title", "") or ""
        if not title:
            continue

        provider = content.get("provider", {})
        publisher = provider.get("displayName", "Unknown") if isinstance(provider, dict) else str(provider or "Unknown")

        link = content.get("canonicalUrl") or content.get("clickThroughUrl") or content.get("link", {})
        link = link.get("url", "#") if isinstance(link, dict) else (link or "#")

        pub_raw = content.get("pubDate", "")
        try:
            dt = datetime.datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
            pub_date = dt.strftime('%Y-%m-%d %H:%M')
        except:
            pub_date = str(pub_raw)[:16] if pub_raw else "Unknown"

        articles.append({
            "title": title,
            "publisher": publisher,
            "link": link,
            "published": pub_date,
            "source": "Yahoo Finance"
        })
    return articles


# ── Google News ─────────────────────────────────────────
def _fetch_google_news(ticker: str) -> list:
    """Fetch stock news from Google News."""
    try:
        country = "IN" if ticker.endswith((".NS", ".BO")) else "US"
        gn = GNews(language="en", country=country, max_results=10, period="7d")
        name = _news_identity(ticker)
        raw = gn.get_news(f'"{name}" stock') or []
        if not raw:
            gn.period = "30d"
            raw = gn.get_news(f'"{name}" stock') or []
    except Exception:
        return []

    articles = []
    for item in raw[:10]:
        title = item.get("title", "") or ""
        if not title:
            continue

        publisher = item.get("publisher", {})
        if isinstance(publisher, dict):
            publisher = publisher.get("title", "Unknown")
        else:
            publisher = str(publisher or "Unknown")

        articles.append({
            "title": title,
            "publisher": publisher,
            "link": item.get("url", "#"),
            "published": item.get("published date", "Unknown"),
            "source": "Google News"
        })
    return articles


# ── Deduplication ───────────────────────────────────────
def _deduplicate(articles: list) -> list:
    """Remove duplicate headlines based on title similarity."""
    seen = set()
    unique = []
    for a in articles:
        # Use first 50 chars as a fingerprint
        key = a["title"][:50].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique


# ── Main Analysis ───────────────────────────────────────
def get_sentiment_analysis(ticker: str):
    """
    Multi-source sentiment analysis:
    1. Fetches news from Yahoo Finance + Google News
    2. Deduplicates headlines
    3. Runs VADER sentiment on each headline
    4. Returns aggregate sentiment profile
    """

    ticker = ticker.strip().upper()
    if not re.fullmatch(r"[A-Z0-9^][A-Z0-9.^=&-]{0,39}", ticker):
        raise ValueError("Enter a valid ticker symbol")

    # Fetch from both sources
    yahoo_articles = _fetch_yahoo_news(ticker)
    google_articles = _fetch_google_news(ticker)

    all_articles = _deduplicate(yahoo_articles + google_articles)

    if not all_articles:
        return {
            "ticker": ticker,
            "status": "no_news",
            "message": "No recent news was available for this symbol. Try again later or check the exchange suffix.",
            "models_used": [],
            "finbert_score": None,
            "finbert_articles_analyzed": 0,
            "overall_sentiment": "Unavailable",
            "overall_score": 0.0,
            "confidence": 0.0,
            "articles_analyzed": 0,
            "sources_used": [],
            "articles": [],
            "sentiment_breakdown": {"positive": 0, "negative": 0, "neutral": 0}
        }

    analyzed = []
    finbert_scores = []
    total_compound = 0.0
    pos_count = neg_count = neu_count = 0

    for a in all_articles:
        scores = _score_with_finbert(a["title"])
        compound = scores["compound"]
        if scores.get("model") == "FinBERT":
            finbert_scores.append(compound)
        total_compound += compound

        if compound >= 0.05:
            label = "Positive"
            pos_count += 1
        elif compound <= -0.05:
            label = "Negative"
            neg_count += 1
        else:
            label = "Neutral"
            neu_count += 1

        analyzed.append({
            **a,
            "sentiment": label,
            "score": round(compound, 3),
            "model": scores.get("model", "VADER"),
            "scores": {
                "positive": round(scores["pos"], 3),
                "negative": round(scores["neg"], 3),
                "neutral": round(scores["neu"], 3),
            }
        })

    n = len(analyzed)
    avg = total_compound / n if n > 0 else 0

    if avg >= 0.15:
        overall = "Bullish"
    elif avg >= 0.05:
        overall = "Slightly Bullish"
    elif avg <= -0.15:
        overall = "Bearish"
    elif avg <= -0.05:
        overall = "Slightly Bearish"
    else:
        overall = "Neutral"

    confidence = min(abs(avg) * 5, 1.0)

    # Which sources contributed
    sources_used = list(set(a["source"] for a in analyzed))

    return {
        "ticker": ticker,
        "status": "ok",
        "finbert_score": sum(finbert_scores) / len(finbert_scores) if finbert_scores else None,
        "finbert_articles_analyzed": len(finbert_scores),
        "models_used": sorted(set(a["model"] for a in analyzed)),
        "overall_sentiment": overall,
        "overall_score": round(avg, 4),
        "confidence": round(confidence, 2),
        "articles_analyzed": n,
        "sources_used": sources_used,
        "articles": analyzed,
        "sentiment_breakdown": {
            "positive": pos_count,
            "negative": neg_count,
            "neutral": neu_count
        }
    }
