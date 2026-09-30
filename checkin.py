#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GLaDOS 自动签到脚本
零第三方依赖，仅使用 Python 标准库，可直接跑在 Windows / Linux / GitHub Actions 上。

环境变量：
  GLADOS_COOKIE   必需。账号 Cookie，格式 koa:sess=xxx; koa:sess.sig=xxx
                  多账号用 & 或换行分隔
  GLADOS_BASE     可选。默认 https://glados.rocks，失败会自动尝试镜像域名
  GLADOS_INSECURE 可选。设为 1 时跳过 SSL 证书校验（企业代理/自签名证书环境用）
  GLADOS_TIMEOUT  可选。超时秒数，默认 30

推送通知（全部可选）：
  PUSHPLUS_TOKEN                        PushPlus（微信推送）
  TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID Telegram
  BARK_URL + BARK_KEY                   Bark（iOS）
"""

import os
import sys
import ssl
import json
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone, timedelta

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

DEFAULT_BASE = os.environ.get("GLADOS_BASE", "https://glados.rocks").rstrip("/")
MIRRORS = ["https://glados.rocks", "https://glados.space", "https://glados.one"]
INSECURE = os.environ.get("GLADOS_INSECURE", "0") == "1"
TIMEOUT = int(os.environ.get("GLADOS_TIMEOUT", "30"))
CN = timezone(timedelta(hours=8))


def log(msg):
    print("[%s] %s" % (datetime.now(CN).strftime("%Y-%m-%d %H:%M:%S"), msg), flush=True)


def build_opener():
    ctx = ssl.create_default_context()
    if INSECURE:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))


def api(opener, base, path, cookie, method="GET", payload=None):
    url = base + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "cookie": cookie,
        "user-agent": UA,
        "accept": "application/json, text/plain, */*",
        "origin": base,
        "referer": base + "/console/checkin",
    }
    if data is not None:
        headers["content-type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with opener.open(req, timeout=TIMEOUT) as resp:
        raw = resp.read().decode("utf-8", "replace")
    try:
        return json.loads(raw)
    except ValueError:
        return {"_raw": raw}


def parse_cookies(raw):
    text = raw.replace("\r", "\n").replace("&", "\n").replace("|", "\n")
    out = []
    for line in text.split("\n"):
        line = line.strip()
        if line and ("koa:sess" in line or "koa:sess.sig" in line):
            if line not in out:
                out.append(line)
    return out


def checkin_one(opener, cookie, idx, total):
    tag = "账号 %d/%d" % (idx, total)
    bases = [DEFAULT_BASE] + [m for m in MIRRORS if m.rstrip("/") != DEFAULT_BASE]
    last_err = ""

    for base in bases:
        try:
            st = api(opener, base, "/api/user/status", cookie)
            data = st.get("data") if isinstance(st, dict) else None
            data = data if isinstance(data, dict) else {}
            left = data.get("leftDays", st.get("leftDays", "?"))
            email = data.get("email", "")

            res = api(opener, base, "/api/user/checkin", cookie, "POST",
                      {"token": "glados.network"})
            msg = res.get("message") or res.get("msg") or res.get("_raw") or ""

            low = str(msg).lower()
            FAIL_WORDS = ("没有权限", "无权限", "权限不足", "未登录", "登录已失效",
                          "unauthorized", "invalid", "expired", "error", "fail")
            REPEAT_WORDS = ("repeat", "already", "已签到", "重复签到")

            if any(w in low for w in FAIL_WORDS):
                ok, note = False, "签到失败，服务端拒绝了请求（多半是 Cookie 失效）"
            elif any(w in low for w in REPEAT_WORDS):
                ok, note = True, "今天已签到过（重复签到，不算失败）"
            elif msg:
                ok, note = True, "签到完成"
            else:
                ok, note = False, "返回内容为空"

            log("%s | %s | 剩余 %s 天 | 服务端返回: %s" % (tag, note, left, msg))
            return {"ok": ok, "tag": tag, "base": base, "left": left,
                    "email": email, "msg": msg}

        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")[:200]
            except Exception:
                pass
            last_err = "HTTP %s %s" % (e.code, body)
            if e.code in (401, 403):
                log("%s | Cookie 已失效或无权访问（%s），请重新获取 Cookie" % (tag, e.code))
                break
        except Exception as e:
            last_err = "%s: %s" % (type(e).__name__, e)

        log("%s | %s 失败（%s），尝试下一个域名..." % (tag, base, last_err))

    return {"ok": False, "tag": tag, "base": "-", "left": "?",
            "email": "", "msg": last_err or "全部域名均失败"}


def notify(title, content):
    pushplus = os.environ.get("PUSHPLUS_TOKEN", "").strip()
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    bark_url = os.environ.get("BARK_URL", "").strip().rstrip("/")
    bark_key = os.environ.get("BARK_KEY", "").strip()

    try:
        if pushplus:
            api(build_opener(), "https://www.pushplus.plus", "/send", "", "POST",
                {"token": pushplus, "title": title, "content": content, "template": "txt"})
            log("已推送 PushPlus")
        if tg_token and tg_chat:
            api(build_opener(), "https://api.telegram.org",
                "/bot%s/sendMessage" % tg_token, "", "POST",
                {"chat_id": tg_chat, "text": title + "\n" + content})
            log("已推送 Telegram")
        if bark_url and bark_key:
            urllib.request.urlopen(
                "%s/%s/%s/%s" % (bark_url, bark_key,
                                 urllib.parse.quote(title),
                                 urllib.parse.quote(content)),
                timeout=TIMEOUT)
            log("已推送 Bark")
    except Exception as e:
        log("推送失败（不影响签到结果）: %s" % e)


def main():
    raw = os.environ.get("GLADOS_COOKIE", "").strip()
    if not raw:
        log("未设置环境变量 GLADOS_COOKIE，退出。")
        log("获取方式：登录 glados.rocks -> F12 -> Network -> 打开 /console/checkin "
            "-> 任意请求 -> Request Headers -> 复制 cookie 值")
        return 2

    cookies = parse_cookies(raw)
    if not cookies:
        log("GLADOS_COOKIE 里没找到 koa:sess 字段，请检查是否复制完整。")
        return 2

    log("=" * 60)
    log("GLaDOS 自动签到开始，共 %d 个账号，主域名 %s" % (len(cookies), DEFAULT_BASE))
    log("=" * 60)

    opener = build_opener()
    results = []
    for i, ck in enumerate(cookies, 1):
        results.append(checkin_one(opener, ck, i, len(cookies)))
        if i < len(cookies):
            time.sleep(3)

    ok = sum(1 for r in results if r["ok"])
    lines = ["%s -> %s | 剩余 %s 天 | %s" % (r["tag"], "成功" if r["ok"] else "失败",
                                             r["left"], r["msg"])
             for r in results]
    summary = "\n".join(lines)
    log("-" * 60)
    log("汇总：%d/%d 成功" % (ok, len(results)))
    print(summary)

    title = "GLaDOS 签到 %d/%d 成功" % (ok, len(results))
    notify(title, summary)

    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
