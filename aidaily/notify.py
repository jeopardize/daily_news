"""构建日报 markdown 消息 + webhook 模式推送。"""
import logging
from datetime import datetime

import requests

log = logging.getLogger(__name__)


def build_markdown(news: list[dict], papers: list[dict]) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    md = [f"# 📡 AI Infra 每日速递 | {today}", ""]
    md.append(f"**📄 前沿论文（{len(papers)}）** · 综述优先")
    for i, p in enumerate(papers, 1):
        tag = "🔥综述" if p.get("is_survey") else "论文"
        md.append(f"**{i}.【{tag}】{p['title']}**")
        md.append(f"{p.get('llm_summary', '')}")
        md.append(f"🔗 arXiv: [{p['link']}]({p['link']})")
        md.append("")
    md.append(f"**📰 行业新闻（{len(news)}）**")
    for i, n in enumerate(news, 1):
        md.append(f"**{i}. {n['title']}**（{n.get('source', '')}）")
        md.append(f"{n.get('llm_summary', '')}")
        md.append(f"🔗 [原文链接]({n['link']})")
        md.append("")
    return "\n".join(md)


def push_webhook(webhook: str, content: str) -> bool:
    if not webhook:
        log.error("未配置 webhook，跳过推送")
        return False
    if len(content.encode("utf-8")) > 4096:
        content = content[:4000] + "\n\n**内容过长已截断**"
    resp = requests.post(webhook, json={"msgtype": "markdown",
                                        "markdown": {"content": content}}, timeout=15)
    ok = resp.ok and resp.json().get("errcode") == 0
    if not ok:
        log.error("webhook 推送失败: %s %s", resp.status_code, resp.text)
    return ok
