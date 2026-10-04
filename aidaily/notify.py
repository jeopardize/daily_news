"""企业微信群机器人推送（markdown 消息，可跳转链接）。"""
import logging

import requests

log = logging.getLogger(__name__)


def push_wechat(cfg: dict, news: list[dict], papers: list[dict]) -> bool:
    webhook = cfg.get("wechat_webhook", "")
    if "你的机器人key" in webhook or not webhook:
        log.error("未配置 wechat_webhook，跳过推送")
        return False

    md = ["## 📡 AI Infra 每日速递", ""]
    md.append(f"> 📅 生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")

    if papers:
        md += ["", f"### 📄 前沿论文（{len(papers)}）"]
        for i, p in enumerate(papers, 1):
            tag = "🔥综述" if p["is_survey"] else "论文"
            md.append(f"{i}. 【{tag}】**{p['title']}**")
            md.append(f"   {p.get('llm_summary', '')}")
            md.append(f"   🔗 [arXiv 链接]({p['link']})")

    if news:
        md += ["", f"### 📰 行业新闻（{len(news)}）"]
        for i, n in enumerate(news, 1):
            src = n.get("source", "")
            md.append(f"{i}. **{n['title']}**（{src}）")
            md.append(f"   {n.get('llm_summary', '')}")
            md.append(f"   🔗 [原文链接]({n['link']})")

    content = "\n".join(md)
    # 企业微信 markdown 上限 4096 字节，超出截断
    if len(content.encode("utf-8")) > 4096:
        content = content[:4090].rsplit("\n", 1)[0] + "\n<details>内容过长已截断</details>"

    resp = requests.post(webhook, json={"msgtype": "markdown",
                                        "markdown": {"content": content}}, timeout=15)
    ok = resp.ok and resp.json().get("errcode") == 0
    if not ok:
        log.error("推送失败: %s %s", resp.status_code, resp.text)
    return ok
