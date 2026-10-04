"""从 RSS 源抓取 AI Infra 相关新闻。"""
import time
import logging
from datetime import datetime, timedelta, timezone

import feedparser
import requests

log = logging.getLogger(__name__)

UA = "Mozilla/5.0 (compatible; AIDaily/1.0)"


def collect_news(cfg: dict) -> list[dict]:
    news_cfg = cfg.get("news", {})
    sources = news_cfg.get("sources", [])
    max_count = int(news_cfg.get("max_count", 5))
    lookback = timedelta(hours=int(news_cfg.get("lookback_hours", 24)))

    items = []
    for src in sources:
        name, url = src.get("name"), src.get("url")
        try:
            feed = feedparser.parse(url, request_headers={"User-Agent": UA})
            for e in feed.entries:
                published = e.get("published_parsed") or e.get("updated_parsed")
                pub_dt = datetime.fromtimestamp(time.mktime(published), tz=timezone.utc) \
                    if published else None
                items.append({
                    "type": "news",
                    "source": name,
                    "title": e.get("title", "").strip(),
                    "link": e.get("link", ""),
                    "summary": (e.get("summary") or "")[:1500],
                    "published": pub_dt.isoformat() if pub_dt else None,
                    "datetime": pub_dt,
                })
        except Exception:
            log.exception("抓取新闻源失败: %s (%s)", name, url)
        time.sleep(1)  # 礼貌间隔

    # 过滤时间窗口（无时间的直接保留）
    cutoff = datetime.now(timezone.utc) - lookback
    recent = [
        it for it in items
        if it["datetime"] is None or it["datetime"] >= cutoff
    ]
    recent.sort(key=lambda x: x["datetime"] or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True)
    return recent[:max_count]
