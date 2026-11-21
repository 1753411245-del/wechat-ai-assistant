# -*- coding: utf-8 -*-
"""打印某个会话最近若干条消息原文，用于确认群消息格式 / @ 写法。
用法：python src/peek.py <wxid 或 xxx@chatroom> [条数]"""
import io, os, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from wechatauto import WeChatDB

TARGET = sys.argv[1] if len(sys.argv) > 1 else "filehelper"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 12

kw = {}
if os.environ.get("WXAI_DB_DIR"):
    kw["db_dir"] = os.environ["WXAI_DB_DIR"]
if os.environ.get("WXAI_ACCOUNT"):
    kw["account"] = os.environ["WXAI_ACCOUNT"]

db = WeChatDB(**kw)
me = str((db.get_self_info() or {}).get("username") or "")
print("SELF:", me, "| TARGET:", TARGET, "| nickname:", db.get_nickname(TARGET))
msgs = list(db.get_messages(TARGET, limit=N) or [])
print("COUNT:", len(msgs))
for m in msgs:
    print("-" * 60)
    print("type=%r sender=%r seq=%r" % (m.get("type"),
                                        m.get("real_sender_id") or m.get("sender_id"),
                                        m.get("sort_seq")))
    print("content=%r" % (m.get("content"),))
