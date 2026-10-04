import os
import yaml

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.environ.get("AID_CONFIG", os.path.join(PROJECT_ROOT, "config.yaml"))
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")


def _load_dotenv() -> None:
    try:
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass


def load_config(path: str = CONFIG_PATH) -> dict:
    _load_dotenv()
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    wecom = cfg.setdefault("wecom", {})
    # 环境变量优先，其次是 config.yaml
    if v := os.environ.get("WECOM_BOT_ID"):
        wecom["bot_id"] = v
    if v := os.environ.get("WECOM_BOT_SECRET"):
        wecom["secret"] = v
    if v := os.environ.get("WECOM_CHATID"):
        wecom["chatid"] = v
    if v := os.environ.get("WECHAT_WEBHOOK"):
        wecom["webhook"] = v

    llm = cfg.setdefault("llm", {})
    if v := os.environ.get("OPENAI_API_KEY"):
        llm["api_key"] = v
    if v := os.environ.get("OPENAI_BASE_URL"):
        llm["base_url"] = v

    return cfg
