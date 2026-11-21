# -*- coding: utf-8 -*-
"""列出当前账号的会话（wxid / 昵称 / 类型 / 未读），用于填写白名单。"""
import io, os, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from wechatauto import WeChatDB

kw = {}
if os.environ.get("WXAI_DB_DIR"):
    kw["db_dir"] = os.environ["WXAI_DB_DIR"]
if os.environ.get("WXAI_ACCOUNT"):
    kw["account"] = os.environ["WXAI_ACCOUNT"]

db = WeChatDB(**kw)
info = db.get_self_info() or {}
print("SELF:", info.get("nick_name") or info.get("nickname"),
      info.get("username") or info.get("wxid"))
rows = list(db.get_sessions(limit=300) or [])
print("TOTAL:", len(rows))
for r in rows:
    u = str(r.get("username") or r.get("wxid") or "")
    try:
        n = db.get_nickname(u)
    except Exception:
        n = "?"
    kind = "GROUP" if u.endswith("@chatroom") else "PRIVATE"
    print("%-32s | %-24s | %s | unread=%s" % (u, n, kind, r.get("unread", 0)))
