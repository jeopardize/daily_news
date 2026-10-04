"""企业微信智能机器人 WebSocket 长连接客户端。

协议: wss://openws.work.weixin.qq.com
- aibot_subscribe 订阅（BotID + Secret）
- 30s 心跳 ping
- aibot_msg_callback 时记录群 chatid（用户需先 @机器人 发一条消息）
- aibot_send_msg 主动推送 markdown 消息
"""
import asyncio
import json
import logging
import os
import time
import uuid

import websockets

log = logging.getLogger(__name__)

WSS_URL = "wss://openws.work.weixin.qq.com"
STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chatids.json"
)


def load_chatids() -> dict:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_chatid(chatid: str) -> None:
    data = load_chatids()
    data[chatid] = int(time.time())
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def latest_chatid() -> str | None:
    data = load_chatids()
    if not data:
        return None
    return max(data, key=data.get)


class WecomBot:
    """长连接模式：listen_forever 与 push_markdown 共用同一条连接。"""

    def __init__(self, bot_id: str, secret: str):
        self.bot_id = bot_id
        self.secret = secret
        self.ws = None
        self.pending: dict[str, asyncio.Future] = {}
        self.connected = asyncio.Event()

    @staticmethod
    def _req_id() -> str:
        return uuid.uuid4().hex

    async def _subscribe(self, ws) -> None:
        req_id = self._req_id()
        await ws.send(json.dumps({
            "cmd": "aibot_subscribe",
            "headers": {"req_id": req_id},
            "body": {"bot_id": self.bot_id, "secret": self.secret},
        }))
        while True:
            frame = json.loads(await ws.recv())
            if frame.get("headers", {}).get("req_id") == req_id:
                if frame.get("errcode", 1) != 0:
                    raise RuntimeError(f"订阅失败: {frame.get('errmsg')}")
                log.info("企业微信长连接订阅成功")
                return

    async def _heartbeat(self, ws) -> None:
        while True:
            await asyncio.sleep(30)
            try:
                await ws.send(json.dumps({
                    "cmd": "ping", "headers": {"req_id": self._req_id()},
                }))
            except Exception:
                return

    def _handle(self, frame: dict) -> None:
        cmd = frame.get("cmd", "")
        req_id = frame.get("headers", {}).get("req_id")
        if cmd.endswith("_callback"):
            log.info("收到帧: cmd=%s body=%s", cmd,
                     json.dumps(frame.get("body", {}), ensure_ascii=False)[:500])
        if cmd.endswith("_callback"):
            body = frame.get("body", {})
            chatid, chattype = body.get("chatid"), body.get("chattype")
            if chattype == "group" and chatid:
                save_chatid(chatid)
                log.info("已记录群 chatid: %s", chatid)
        else:
            fut = self.pending.pop(req_id, None)
            if fut and not fut.done():
                fut.set_result(frame)

    async def listen_forever(self) -> None:
        """断线自动重连。"""
        while True:
            try:
                async with websockets.connect(WSS_URL, ping_interval=None) as ws:
                    await self._subscribe(ws)
                    self.ws = ws
                    self.connected.set()
                    hb = asyncio.create_task(self._heartbeat(ws))
                    try:
                        async for raw in ws:
                            self._handle(json.loads(raw))
                    finally:
                        hb.cancel()
            except Exception as e:
                log.warning("长连接断开: %s，5 秒后重连", e)
            finally:
                self.ws = None
                self.connected.clear()
                for fut in self.pending.values():
                    if not fut.done():
                        fut.set_exception(RuntimeError("connection lost"))
                self.pending.clear()
            await asyncio.sleep(5)

    async def _request(self, body: dict, timeout: float = 30) -> dict:
        await asyncio.wait_for(self.connected.wait(), timeout=60)
        req_id = self._req_id()
        fut = asyncio.get_running_loop().create_future()
        self.pending[req_id] = fut
        await self.ws.send(json.dumps({
            "cmd": "aibot_send_msg",
            "headers": {"req_id": req_id},
            "body": body,
        }))
        return await asyncio.wait_for(fut, timeout=timeout)

    async def push_markdown(self, content: str, chatid: str | None = None) -> None:
        chatid = chatid or latest_chatid()
        if not chatid:
            raise RuntimeError(
                "尚未获取 chatid：请先在企业微信群里 @机器人 随便发一条消息"
            )
        frame = await self._request({
            "chatid": chatid,
            "chat_type": 2,
            "msgtype": "markdown",
            "markdown": {"content": content},
        })
        if frame.get("errcode", 1) != 0:
            raise RuntimeError(f"推送失败: errcode={frame.get('errcode')} {frame.get('errmsg')}")
        log.info("推送到群 %s 成功", chatid)


async def push_standalone(bot_id: str, secret: str, content: str, chatid: str) -> None:
    """一次性短连接推送（用于 once 模式调试）。"""
    if not chatid:
        raise RuntimeError("缺少 chatid：请先在群里 @机器人 发一条消息，或在 config 写入 chatid")
    async with websockets.connect(WSS_URL, ping_interval=None) as ws:
        req_id = uuid.uuid4().hex
        await ws.send(json.dumps({
            "cmd": "aibot_subscribe",
            "headers": {"req_id": req_id},
            "body": {"bot_id": bot_id, "secret": secret},
        }))
        while True:
            frame = json.loads(await ws.recv())
            if frame.get("headers", {}).get("req_id") == req_id:
                if frame.get("errcode", 1) != 0:
                    raise RuntimeError(f"订阅失败: {frame.get('errmsg')}")
                break
        req_id = uuid.uuid4().hex
        await ws.send(json.dumps({
            "cmd": "aibot_send_msg",
            "headers": {"req_id": req_id},
            "body": {
                "chatid": chatid, "chat_type": 2,
                "msgtype": "markdown", "markdown": {"content": content},
            },
        }))
        while True:
            frame = json.loads(await ws.recv())
            if frame.get("headers", {}).get("req_id") == req_id:
                if frame.get("errcode", 1) != 0:
                    raise RuntimeError(f"推送失败: errcode={frame.get('errcode')} {frame.get('errmsg')}")
                log.info("推送成功")
                return
