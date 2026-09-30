# GLaDOS 自动签到

零依赖 Python 脚本（只用标准库），支持多账号、多域名自动回退、可选推送通知。
两种用法：**GitHub Actions（推荐）** 或 **本机定时任务**。

---

## 第一步：拿到 Cookie（最关键）

1. 浏览器登录 https://glados.rocks
2. 打开签到页 https://glados.rocks/console/checkin
3. 按 `F12` 打开开发者工具 → **Network（网络）** 标签
4. 刷新页面（或点一下页面上的 Checkin 按钮）
5. 左侧请求列表里找 `checkin` 或 `status`，点它 → 右侧 **Headers** → **Request Headers**
6. 找到 `cookie:`，复制完整的值，形如：

```
koa:sess=eyJ1c2VySWQiOjEyMzQ1Nn0=; koa:sess.sig=AbCdEf123456
```

> **注意**
> - 必须包含 `koa:sess` 和 `koa:sess.sig` 两段，只复制一段会失败。
> - Cookie 等同于账号密码，**不要泄露、不要提交到公开仓库**（放到 GitHub Secrets 里）。
> - Cookie 会过期（一般一个月左右），过期后脚本会报 401，重新抓一次即可。

---

## 第二步 A：用 GitHub Actions（推荐，最省心）

1. 在 GitHub 上新建仓库，**私有**仓库（Public 也行，但 Secrets 才是安全的重点）
2. 把本目录下的 `checkin.py` 和 `.github/workflows/checkin.yml` 传上去，目录结构保持一致：

```
your-repo/
├── checkin.py
└── .github/
    └── workflows/
        └── checkin.yml
```

3. 进入仓库 **Settings → Secrets and variables → Actions → New repository secret**

| Secret 名称 | 是否必填 | 说明 |
|---|---|---|
| `GLADOS_COOKIE` | ✅ | 第一步拿到的 Cookie，多账号用 `&` 分隔 |
| `GLADOS_BASE` | 可选 | 主域名，默认 `https://glados.rocks` |
| `PUSHPLUS_TOKEN` | 可选 | 微信推送，token 在 pushplus.plus 获取 |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | 可选 | Telegram 推送 |
| `BARK_URL` / `BARK_KEY` | 可选 | iOS Bark 推送 |

4. 打开 **Actions** 标签页，第一次会提示启用，点 "I understand my workflows, go ahead and enable them"
5. 点右侧 **Run workflow** 手动跑一次，看日志确认签到成功

之后每天北京时间 09:30 和 21:30 各跑一次（双保险）。

> **GitHub 的坑**：免费账户的定时任务在高峰期会延迟，甚至偶尔漏跑。所以配了两个时间点互为备份。
> 另外 GitHub 对**长时间无提交**的仓库会自动停用定时任务——如果 Actions 不跑了，随便 commit 一下就能重新激活。

---


## 第三步：确认真的在涨天数

签到成功后，去 https://glados.rocks/console/checkin 看剩余天数，应该每次 +1。

脚本每次运行都会打印服务端原始返回值，方便你直接判断：

- `Checkin successful! 1 days added` → 正常
- 含 `Repeats` / `already` → 今天已签过，不算失败
- `HTTP 401` → Cookie 过期，重新抓

---

## 常见问题

**Q：Cookie 多久失效？**
一般一个月左右，也可能因为改密码、异地登录提前失效。失效时脚本会明确提示 401。

**Q：签到能无限续期吗？**
每天签到 +1 天，理论上可以一直续。但 GLaDOS 随时可能改规则，别当永久资产。

**Q：报 SSL 证书错误（公司网络常见）？**
设置环境变量 `GLADOS_INSECURE=1` 跳过证书校验。

**Q：多账号怎么配？**
Cookie 之间用 `&` 分隔即可，脚本会逐个签到并在账号之间自动延迟 3 秒。

**Q：能白嫖多少流量？**
普通邮箱注册送 3 天 / 10G；`.edu` 教育邮箱可申请 Education Plan，360 天 / 50G。

**Q：公司网络（代理 + 自签名证书）下 git 推不上去？**
公司代理会做 SSL 中间人替换证书，git 默认会报：

```
fatal: unable to access 'https://github.com/.../':
SSL certificate OpenSSL verify result: self-signed certificate in certificate chain (19)
```

推送时关掉证书校验即可：

```bash
git -c http.sslVerify=false push -u origin main
```

另外公司代理通常还会拦 `api.github.com`（表现为 502 Bad Gateway），这意味着
**建仓库、写 Secret、触发 workflow 都只能走网页**，脚本帮不上忙。

---

## 附：本机可用的推送脚本

`push_to_github.py`（在本目录的上一层）封装了上面这些坑：填入 GitHub 用户名、
PAT 和仓库名后运行，会自动关闭 SSL 校验完成推送，并在推送成功后把远端地址里的
token 抹掉，不会明文留在 `.git/config` 里。仓库仍需你在网页上先建好。
