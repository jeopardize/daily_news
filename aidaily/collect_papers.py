"""从 arXiv 抓取 AI Infra 相关论文，综述优先，可配置每天数量。"""
import logging
import re
from datetime import datetime, timedelta, timezone

import arxiv
import requests

log = logging.getLogger(__name__)

SURVEY_PAT = re.compile(r"\b(survey|review|overview|taxonomy|benchmark(ing)?)\b", re.I)


def collect_papers(cfg: dict) -> list[dict]:
    p_cfg = cfg.get("papers", {})
    categories = p_cfg.get("categories", ["cs.DC", "cs.LG"])
    keywords = p_cfg.get("keywords", [])
    max_count = int(p_cfg.get("max_count", 5))
    lookback_days = int(p_cfg.get("lookback_days", 3))
    prefer_survey = bool(p_cfg.get("prefer_survey", True))

    since = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y%m%d")
    query = " OR ".join(f"cat:{c}" for c in categories)
    client = arxiv.Client(page_size=100, delay_seconds=3)

    try:
        search = arxiv.Search(query=query, sort_by=arxiv.SortCriterion.SubmittedDate,
                              max_results=500)
        results = list(client.results(search))
    except Exception:
        log.exception("arXiv 拉取失败")
        return []

    papers = []
    kw_lower = [k.lower() for k in keywords]
    for r in results:
        if r.published and r.published.replace(tzinfo=timezone.utc) < \
                datetime.now(timezone.utc) - timedelta(days=lookback_days):
            continue
        text = f"{r.title} {r.summary}".lower()
        if kw_lower and not any(k in text for k in kw_lower):
            continue
        is_survey = bool(SURVEY_PAT.search(r.title))
        papers.append({
            "type": "paper",
            "title": r.title.replace("\n", " ").strip(),
            "link": r.get_short_id() and f"https://arxiv.org/abs/{r.get_short_id().split('v')[0]}",
            "summary": (r.summary or "").replace("\n", " ")[:2000],
            "authors": ", ".join(a.name for a in r.authors[:4]),
            "is_survey": is_survey,
            "datetime": r.published.replace(tzinfo=timezone.utc) if r.published else None,
        })

    # 固定顺序打不打乱：综述优先，其余按时间倒序
    if prefer_survey:
        surveys = sorted([p for p in papers if p["is_survey"]],
                         key=lambda x: x["datetime"] or datetime.min, reverse=True)
        normal = sorted([p for p in papers if not p["is_survey"]],
                        key=lambda x: x["datetime"] or datetime.min, reverse=True)
        ordered = surveys + normal
        log.info("命中 %d 篇（其中综述 %d 篇），取前 %d 篇", len(ordered), len(surveys), max_count)
    else:
        ordered = sorted(papers, key=lambda x: x["datetime"] or datetime.min, reverse=True)
        log.info("命中 %d 篇，取前 %d 篇", len(ordered), max_count)
    return ordered[:max_count]
