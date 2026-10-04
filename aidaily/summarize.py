"""LLM 中文摘要（OpenAI 兼容接口）。"""
import asyncio
import logging

from openai import AsyncOpenAI

log = logging.getLogger(__name__)

SYS_PROMPT = (
    "你是 AI 基础设施领域的资深编辑。用中文对给定内容写一段简洁摘要，"
    "突出：它是什么、核心创新/事件、为什么对 AI Infra 从业者重要。"
    "不要输出标题和序号，控制在指定字数内。"
)


async def _summarize_one(client: AsyncOpenAI, cfg: dict, item: dict,
                         sem: asyncio.Semaphore) -> dict:
    model = cfg["llm"].get("model", "gpt-4o-mini")
    max_words = int(cfg["llm"].get("max_words", 300))
    timeout = cfg["llm"].get("timeout", 60)
    user_prompt = (
        f"类型: {'arXiv论文' if item['type'] == 'paper' else '新闻'}\n"
        f"标题: {item['title']}\n"
        f"正文/摘要: {item['summary']}\n"
        f"请写不超过 {max_words//2} 个汉字的中文摘要。"
    )
    async with sem:
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYS_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                timeout=timeout,
            )
            item["llm_summary"] = resp.choices[0].message.content.strip()
        except Exception as e:
            log.warning("LLM 摘要失败 (%s): %s", item["title"][:40], e)
            item["llm_summary"] = item["summary"][:300]  # 兜底：原文截取
    return item


async def summarize_items(cfg: dict, items: list[dict]) -> list[dict]:
    if not items:
        return []
    llm = cfg["llm"]
    api_key = (llm.get("api_key") or "").strip()
    # key 缺失或仍是占位符时直接走原文兜底
    if not api_key or not api_key.isascii() or "API_KEY" in api_key.upper():
        log.warning("LLM api_key 未配置，使用原文截取作为摘要")
        for it in items:
            it["llm_summary"] = it["summary"][:300]
        return items
    client = AsyncOpenAI(base_url=llm["base_url"], api_key=api_key)
    sem = asyncio.Semaphore(int(llm.get("max_concurrency", 5)))
    return list(await asyncio.gather(*[_summarize_one(client, cfg, it, sem) for it in items]))
