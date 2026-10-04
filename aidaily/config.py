import os
import yaml

CONFIG_PATH = os.environ.get(
    "AID_CONFIG",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml"),
)


def load_config(path: str = CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # 允许通过环境变量覆盖敏感字段（服务器部署时更方便）
    webhook = os.environ.get("WECHAT_WEBHOOK")
    if webhook:
        cfg["wechat_webhook"] = webhook

    llm = cfg.setdefault("llm", {})
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        llm["api_key"] = api_key
    base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        llm["base_url"] = base_url

    return cfg
