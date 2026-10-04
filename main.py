"""AI Infra 每日速递：抓新闻 + arXiv 论文 → LLM 中文摘要 → 企业微信推送。

用法:
  python main.py once     # 立即执行一次（调试用）
  python main.py listen   # 仅启动长连接监听（等待群里 @机器人 以记录 chatid）
  python main.py run      # 常驻运行：长连接 + 按 config.yaml 的 schedule 定时推送
"""
import asyncio
import logging
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

from aidaily.config import load_config
from aidaily.collect_news import collect_news
from aidaily.collect_papers import collect_papers
from aidaily.summarize import summarize_items
from aidaily.notify import build_markdown, push_webhook
from aidaily.wecom_ws import WecomBot, latest_chatid, push_standalone

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("main")


async def run_daily(cfg: dict, bot: WecomBot | None = None):
    papers = await asyncio.to_thread(collect_papers, cfg)
    news = await asyncio.to_thread(collect_news, cfg)
    log.info("抓取完成: %d 篇论文, %d 条新闻", len(papers), len(news))

    items = await summarize_items(cfg, papers + news) if (papers or news) else []
    papers_llm = [it for it in items if it["type"] == "paper"]
    news_llm = [it for it in items if it["type"] == "news"]
    content = build_markdown(news_llm, papers_llm)

    wecom = cfg.get("wecom", {})
    mode = wecom.get("mode", "webhook")
    if mode == "bot":
        chatid = wecom.get("chatid") or None
        if bot:  # run 模式：复用长连接
            await bot.push_markdown(content, chatid=chatid)
        else:    # once 模式：临时短连接
            await push_standalone(wecom["bot_id"], wecom["secret"],
                                  content, chatid or latest_chatid() or "")
    else:
        await asyncio.to_thread(push_webhook, wecom.get("webhook", ""), content)


async def run_service(cfg: dict):
    wecom = cfg.get("wecom", {})
    bot = None
    tasks = []
    if wecom.get("mode") == "bot" and wecom.get("bot_id") and wecom.get("secret"):
        bot = WecomBot(wecom["bot_id"], wecom["secret"])
        tasks.append(bot.listen_forever())
        log.info("长连接监听已启动（如未收到过 @机器人 消息，请先在群里 @机器人 一次）")

    sched = AsyncIOScheduler(timezone=pytz.timezone(cfg["push"].get("timezone", "Asia/Shanghai")))
    for expr in cfg["push"]["schedule"]:
        minute, hour, *_ = expr.split()
        sched.add_job(run_daily, "cron", args=[cfg, bot],
                      hour=int(hour), minute=int(minute))
        log.info("定时任务: 每天 %s:%s", hour.zfill(2), minute.zfill(2))
    sched.start()
    tasks.append(asyncio.Event().wait())  # 保持常驻
    await asyncio.gather(*tasks)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("once", "run", "listen"):
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "once":
        asyncio.run(run_daily(load_config()))
    elif cmd == "listen":
        cfg = load_config()
        wecom = cfg["wecom"]
        asyncio.run(WecomBot(wecom["bot_id"], wecom["secret"]).listen_forever())
    else:
        asyncio.run(run_service(load_config()))


if __name__ == "__main__":
    main()
