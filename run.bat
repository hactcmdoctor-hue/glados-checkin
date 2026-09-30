@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM ============================================================
REM  GLaDOS 自动签到 - Windows 本地运行入口
REM  把下面的 Cookie 换成你自己的（登录 glados.rocks 后 F12 抓取）
REM  本机定时任务请直接调用本文件
REM ============================================================

set "GLADOS_COOKIE=在这里粘贴你的Cookie，形如 koa:sess=xxx; koa:sess.sig=yyy"

REM 可选：公司代理/自签名证书环境报 SSL 错误时，取消下一行注释
REM set "GLADOS_INSECURE=1"

REM 可选：PushPlus 微信推送
REM set "PUSHPLUS_TOKEN=your_pushplus_token"

echo.
echo GLaDOS 自动签到
echo ================

if "%GLADOS_COOKIE%"=="在这里粘贴你的Cookie，形如 koa:sess=xxx; koa:sess.sig=yyy" (
    echo [错误] 请先编辑 run.bat，把 GLADOS_COOKIE 换成你自己的 Cookie。
    echo.
    echo 获取方法：登录 glados.rocks -^> 打开 /console/checkin -^> F12 -^> Network
    echo           -^> 点 checkin 或 status 请求 -^> Request Headers -^> 复制 cookie 值
    echo.
    pause
    exit /b 1
)

python checkin.py

echo.
echo 执行完毕，按任意键关闭...
pause >nul
