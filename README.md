# AI Infra 每日速递

每天自动抓取 **AI Infra 相关新闻**（RSS）和 **arXiv 前沿论文**（综述优先），用 LLM 生成中文摘要，并通过**企业微信群机器人**推送到微信。每条新闻/论文都附带可点击跳转的原文/arXiv 链接。

## 功能特性

- 📄 **论文抓取**：按 arXiv 分类（cs.DC / cs.LG / cs.AR 等）+ 关键词过滤，**综述（survey/review/overview）永远排在最前**
- 📰 **新闻抓取**：RSS 源可自行增删，只保留最近 24h 内的内容
- 🤖 **LLM 中文摘要**：OpenAI 兼容接口（官方 API / 中转站均可），失败自动降级为原文截取
- 📲 **企业微信推送**：群机器人 webhook，一条消息含全部内容，所有条目可点击跳转
- ⏰ **频率/数量可调**：全部集中在 `config.yaml`，改完重启服务即生效

## 快速开始

### 1. 准备企业微信机器人

1. 在企业微信里建一个群（或用现有群）
2. 群设置 → **群机器人** → **添加机器人**，复制 webhook 地址
3. 地址形如 `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxx`

> 手机微信里关注“企业微信插件”即可在微信内收到群消息。

### 2. 准备 LLM API Key

任意 OpenAI 兼容服务均可：官方 `https://api.openai.com/v1`，或使用中转站地址。

### 3. 修改配置

编辑 `config.yaml`：

```yaml
push:
  schedule:
    - "30 8 * * *"        # 每天早上 8:30 推送，cron 表达式，可加多个
  timezone: "Asia/Shanghai"

wechat_webhook: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=填你的key"

llm:
  base_url: "https://api.openai.com/v1"
  api_key: "填你的API_KEY"
  model: "gpt-4o-mini"

news:
  max_count: 5            # 每天新闻条数
  sources:                # RSS 源，可增删
    - name: "Hacker News"
      url: "https://hnrss.org/newest?q=AI"

papers:
  max_count: 5            # 每天论文条数
  prefer_survey: true     # 综述优先
  lookback_days: 7        # 回看最近几天
  keywords:               # AI Infra 关键词，可增删
    - "LLM inference"
    - "GPU cluster"
```

### 4. 本地试跑一次

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python main.py once
```

看到 `推送成功 ✅` 即配置正确，微信群里应已收到消息。

## 部署到 Linux 服务器（systemd 常驻）

```bash
# 1. 上传代码（本地执行）
rsync -av --exclude venv --exclude .git daily_news/ root@你的服务器IP:/opt/daily_news/

# 2. 服务器上安装依赖
ssh root@你的服务器IP
cd /opt/daily_news
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# 3. 先手动验证一次
venv/bin/python main.py once

# 4. 注册 systemd 服务，开机自启、崩溃自动重启
cp daily_news.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now daily_news

# 5. 查看状态和日志
systemctl status daily_news
journalctl -u daily_news -f
```

> `daily_news.service` 中默认的部署路径是 `/opt/daily_news`，如部署到其他目录请同步修改。

## 敏感信息替代方案（推荐生产使用）

不在 `config.yaml` 里写 key，改用环境变量（优先级更高）：

```bash
export WECHAT_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
export OPENAI_API_KEY="sk-xxx"
export OPENAI_BASE_URL="https://api.openai.com/v1"   # 可选
```

在 `daily_news.service` 的 `[Service]` 段加一行 `EnvironmentFile=/opt/daily_news/.env`，key 全部写在服务器上的 `.env` 文件（不要提交到 git）。

## 常用调整速查

| 想改什么 | 改哪里 |
|---|---|
| 每天推送几次、几点推 | `push.schedule`（cron 表达式） |
| 每天推送论文数量 | `papers.max_count` |
| 每天推送新闻数量 | `news.max_count` |
| 只推综述？ | `papers.prefer_survey: true/false` |
| 换 LLM/模型 | `llm.base_url`、`llm.model` |
| 增删新闻源 | `news.sources` |
| 论文关键词/分类 | `papers.keywords`、`papers.categories` |

改完配置执行 `systemctl restart daily_news` 生效。

## 项目结构

```
daily_news/
├── main.py               # 入口：once=立即跑一次 / run=常驻定时
├── config.yaml           # 所有可调参数
├── daily_news.service    # systemd 服务文件
├── requirements.txt
└── aidaily/
    ├── config.py         # 配置加载，支持环境变量覆盖
    ├── collect_news.py   # RSS 新闻抓取
    ├── collect_papers.py # arXiv 论文抓取（综述优先）
    ├── summarize.py      # LLM 中文摘要（异步并发）
    └── notify.py         # 企业微信推送
```
