"""AI Infra 每日速递：抓新闻 + arXiv 论文 → LLM 中文摘要 → 企业微信推送。

用法:
  python main.py once     # 立即执行一次（调试用）
  python main.py run      # 常驻运行，按 config.yaml 的 schedule 定时推送
"""
import logging
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from pytz import timezone as tz

from aidaily.config import load_config
from aidaily.collect_news import collect_news
from aidaily.collect_papers import collect_papers
from aidaily.summarize import summarize_items
from aidaily.notify import push_wechat

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("main")


def run_once():
    cfg = load_config()
    log.info("开始抓取 %d 篇论文 / %d 条新闻...",
             int(cfg["papers"].get("max_count", 5)),
             int(cfg["news"].get("max_count", 5)))
    papers = collect_papers(cfg)
    news = collect_news(cfg)
    log.info("抓取完成: %d 篇论文, %d 条新闻", len(papers), len(news))

    items = papers + news
    items = __import__("asyncio").run(summarize_items(cfg, items)) if items else []
    papers_llm = [it for it in items if it["type"] == "paper"]
    news_llm = [it for it in items if it["type"] == "news"]

    ok = push_wechat(cfg, news_llm, papers_llm)
    log.info("推送%s", "成功 ✅" if ok else "失败/跳过 ❌")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("once", "run"):
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "once":
        run_once()
        return

    cfg = load_config()
    sched = BlockingScheduler(timezone=tz(cfg["push"].get("timezone", "Asia/Shanghai")))
    for expr in cfg["push"]["schedule"]:
        minute, hour, *_ = expr.split()
        sched.add_job(run_once, "cron", hour=int(hour), minute=int(minute))
        log.info("定时任务已注册: 每天 %s:%s", hour.zfill(2), minute.zfill(2))
    sched.start()


if __name__ == "__main__":
    main()
