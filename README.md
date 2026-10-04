# AI Infra 每日速递

每天自动抓取 **AI Infra 相关新闻**（RSS）和 **arXiv 前沿论文**（综述优先），用 LLM 生成中文摘要，并通过**企业微信群机器人**推送到微信。每条新闻/论文都附带可点击跳转的原文/arXiv 链接。

## 功能特性

- 📄 **论文抓取**：按 arXiv 分类（cs.DC / cs.LG / cs.AR 等）+ 关键词过滤，**综述（survey/review/overview）永远排在最前**
- 📰 **新闻抓取**：RSS 源可自行增删，只保留最近 24h 内的内容
- 🤖 **LLM 中文摘要**：OpenAI 兼容接口（官方 API / 中转站均可），失败自动降级为原文截取
- 📲 **企业微信推送**：支持两种方式——管理后台「智能机器人」**长连接模式**（无需公网 URL）或群机器人 webhook，一条消息含全部内容，所有条目可点击跳转
- ⏰ **频率/数量可调**：全部集中在 `config.yaml`，改完重启服务即生效

## 快速开始

### 1. 准备企业微信推送（二选一）

**方式 A：智能机器人 + 长连接（推荐）**

1. 登录 [企业微信管理后台](https://work.weixin.qq.com) → 管理工具 → **智能机器人** → 创建机器人
2. 创建页面底部选择 **API 模式创建**，连接方式选 **长连接**
3. 记下 **Bot ID** 和 **Secret**
4. 保存后，把机器人**添加到企业微信内部群**，并在群里 **@机器人 随便发一条消息**（首次必须，否则服务端不会下发群 chatid，无法主动推送）

**方式 B：群机器人 webhook**

1. 在企业微信群里：群设置 → 群机器人 → 添加机器人
2. 复制形如 `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxx` 的地址

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

wecom:
  mode: "bot"             # bot=长连接模式 / webhook=群机器人模式
  bot_id: "填BotID"       # 方式A
  secret: "填Secret"      # 方式A
  chatid: ""              # 方式A：留空自动记录（需先@机器人一次）
  webhook: ""             # 方式B

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

看到 `推送成功` 即配置正确，微信群里应已收到消息。
（长连接模式下若提示"尚未获取 chatid"，先在群里 @机器人 发一条消息再重试。）

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

不在 `config.yaml` 里写 key，改用 `.env` 文件或环境变量（优先级更高，配置加载器会自动读取项目根目录的 `.env`）：

```bash
# .env 示例（已被 .gitignore 忽略，不会提交）
WECOM_BOT_ID=xxx
WECOM_BOT_SECRET=xxx
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
```

```bash
export WECHAT_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"  # webhook 模式
export WECOM_BOT_ID="xxx"      # 长连接模式
export WECOM_BOT_SECRET="xxx"
```

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
├── main.py               # 入口：once=立即跑一次 / listen=长连接监听 / run=常驻定时
├── config.yaml           # 所有可调参数
├── daily_news.service    # systemd 服务文件
├── requirements.txt
└── aidaily/
    ├── config.py         # 配置加载，支持 .env / 环境变量覆盖
    ├── collect_news.py   # RSS 新闻抓取
    ├── collect_papers.py # arXiv 论文抓取（综述优先）
    ├── summarize.py      # LLM 中文摘要（异步并发）
    ├── notify.py         # 日报 markdown 构建 + webhook 推送
    └── wecom_ws.py       # 企业微信智能机器人长连接客户端
```
