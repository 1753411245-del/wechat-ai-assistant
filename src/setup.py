# -*- coding: utf-8 -*-
"""交互式配置向导：探测账号 → 列出会话 → 生成 config.env。

    python src/setup.py

任何微信账号都能跑这一次，之后 quickstart.bat / service.bat 直接启动。
"""
import io, os, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, "config.env")

DEFAULT_PERSONA = ("你是我的私人助理，回复简短口语化，80字内，不用markdown；"
                   "问价格/库存/承诺时不要自己编，说“我帮您问下本人，稍等”")


def ask(prompt, default=""):
    s = input("%s%s: " % (prompt, ("[%s]" % default) if default else "")).strip()
    return s or default


def main():
    try:
        from wechatauto import WeChatDB
    except ImportError:
        print("[X] 没装依赖，先运行 quickstart.bat（或 pip install wechatauto-replica --no-deps）")
        return 1
    try:
        from wechatauto import list_accounts
    except ImportError:
        def list_accounts(db_dir=None):
            return []

    print("=" * 62)
    print("微信 AI 助手 · 配置向导")
    print("=" * 62)

    db_dir = ask("微信数据目录（直接回车=自动探测；找不到时再填）", "")
    kw = {}
    if db_dir:
        kw["db_dir"] = db_dir

    accounts = []
    try:
        accounts = list_accounts(db_dir or None) or []
    except Exception as e:
        print("  (扫描账号失败：%r)" % (e,))
    if len(accounts) > 1:
        print("\n检测到多个微信账号：")
        for i, a in enumerate(accounts, 1):
            print("  %d) %s  %s" % (i, a.get("account"), a.get("self_nick") or ""))
        pick = ask("用哪个（序号）", "1")
        try:
            kw["account"] = accounts[int(pick) - 1]["account"]
        except Exception:
            pass

    print("\n[1/5] 打开本地数据库 …")
    try:
        db = WeChatDB(**kw)
    except Exception as e:
        print("[X] 打开失败：%r" % (e,))
        print("    常见原因：微信没登录 / 精简版 / 数据目录不在默认位置")
        return 1
    info = db.get_self_info() or {}
    me = info.get("username") or info.get("wxid") or "?"
    nick = info.get("nick_name") or info.get("nickname") or "?"
    print("    账号：%s (%s)" % (nick, me))

    print("\n[2/5] 会话列表")
    rows = list(db.get_sessions(limit=200) or [])
    for i, r in enumerate(rows, 1):
        u = str(r.get("username") or "")
        try:
            n = db.get_nickname(u)
        except Exception:
            n = "?"
        kind = "群" if u.endswith("@chatroom") else "私聊"
        print("  %3d) %-22s %-24s %s" % (i, n[:22], u, kind))

    print("\n[3/5] 要接管哪些会话？")
    print("    输入序号，逗号分隔（如 3,7,12）；直接回车 = 不指定，自动接管所有私聊")
    pick = ask("    序号", "")
    watch = []
    for tok in pick.replace("，", ",").split(","):
        tok = tok.strip()
        if tok.isdigit() and 1 <= int(tok) <= len(rows):
            watch.append(str(rows[int(tok) - 1].get("username") or ""))

    at_only = ask("    群里只回复 @ 机器人？(y/n)", "y").lower().startswith("y")
    at_name = ask("    群里 @ 它时的昵称（多个用逗号；留空=自动识别）", "")

    print("\n[4/5] 模型")
    base = ask("    OpenAI 兼容地址", "https://api.deepseek.com/v1")
    model = ask("    模型名", "deepseek-chat")
    key = ask("    API Key", "")
    persona = ask("    人设（一句话）", DEFAULT_PERSONA)
    digest = ask("    每天几点发汇总到文件传输助手（留空=关闭）", "21:00")

    print("\n[5/5] 写入配置 …")
    lines = [
        "# 微信 AI 助手配置（UTF-8）。改完重启 service.bat 生效。",
        "WXAI_WATCH=%s" % ",".join(watch),
        "WXAI_AUTO_PRIVATE=%d" % (0 if watch else 1),
        "WXAI_AT_ONLY=%d" % (1 if at_only else 0),
        "WXAI_AT_NAME=%s" % at_name,
        "WXAI_HINT=我这边听不了语音，打字说下呗",
        "WXAI_MIN_GAP=8",
        "WXAI_MAX_REPLIES_PER_MIN=10",
        "WXAI_SKIP_PREFIX=gh_,newsapp,brandsessionholder,filehelper,fmessage,medianote,floatbottle,qqmail,@openim,gamelife",
        "WXAI_ESCALATE=1",
        "WXAI_ESCALATE_TO=filehelper",
        "WXAI_DIGEST_TO=filehelper",
        "WXAI_DIGEST_AT=%s" % digest,
        "WXAI_DIGEST_EVERY=0",
        "WXAI_BASE_URL=%s" % base,
        "WXAI_MODEL=%s" % model,
        "OPENAI_API_KEY=%s" % key,
        "WXAI_PERSONA=%s" % persona,
    ]
    if kw.get("db_dir"):
        lines.insert(1, "WXAI_DB_DIR=%s" % kw["db_dir"])
    if kw.get("account"):
        lines.insert(2, "WXAI_ACCOUNT=%s" % kw["account"])
    with io.open(ENV, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print("    OK -> %s" % ENV)
    print("\n下一步：双击 quickstart.bat（首次）或 service.bat（日常）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
