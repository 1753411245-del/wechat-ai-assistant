# -*- coding: utf-8 -*-
"""读 chat_log.db，生成今日对话摘要（文本 / HTML 看板）。

    python tools/report.py                 # 打印今日摘要
    python tools/report.py --html tools/report.html   # 生成网页看板
    python tools/report.py --days 3        # 看最近 3 天
"""
import argparse
import html
import io
import os
import sqlite3
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "chat_log.db")

T = {
    "title": "\u5fae\u4fe1 AI \u52a9\u624b\u00b7\u5bf9\u8bdd\u770b\u677f",
    "today": "\u4eca\u65e5",
    "chat": "\u4f1a\u8bdd",
    "cnt": "\u6761\u6570",
    "ask": "\u5bf9\u65b9\u8bf4",
    "ans": "AI \u56de",
    "time": "\u65f6\u95f4",
    "none": "\u8fd8\u6ca1\u6709\u8bb0\u5f55\uff08\u673a\u5668\u4eba\u56de\u590d\u540e\u4f1a\u81ea\u52a8\u5199\u5165\uff09",
    "total": "\u5171",
}


def rows(since):
    if not os.path.exists(DB):
        return []
    c = sqlite3.connect(DB)
    try:
        return c.execute(
            "SELECT ts, chat, who, user_text, ai_text FROM chat_log "
            "WHERE ts >= ? ORDER BY ts DESC", (since,)).fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        c.close()


def text_report(since):
    data = rows(since)
    if not data:
        print(T["none"])
        return
    by = {}
    for ts, chat, who, q, a in data:
        by.setdefault(who or chat, []).append((ts, q, a))
    print("%s %s %d %s\uff0c%d %s" % (T["today"], T["total"], len(by), T["chat"],
                                     len(data), T["cnt"]))
    for name, items in by.items():
        print("\n%s%s\uff08%d %s\uff09" % ("", name, len(items), T["cnt"]))
        for ts, q, a in items[:3]:
            print("  %s  %s: %s" % (time.strftime("%H:%M", time.localtime(ts)), T["ask"], (q or "-")[:50]))
            print("        %s: %s" % (T["ans"], (a or "-")[:50]))


def html_report(since, out):
    data = rows(since)
    by = {}
    for ts, chat, who, q, a in data:
        by.setdefault(who or chat, []).append((ts, q, a))
    e = html.escape
    parts = [
        "<!doctype html><meta charset='utf-8'>",
        "<title>%s</title>" % T["title"],
        "<style>body{font:14px/1.6 -apple-system,'Microsoft YaHei',sans-serif;"
        "background:#0f1115;color:#e6e6e6;margin:24px}",
        "h1{font-size:18px;margin:0 0 4px}.sub{color:#8a8a8a;margin-bottom:18px}",
        ".card{background:#171a21;border:1px solid #242833;border-radius:10px;"
        "padding:14px 16px;margin:12px 0}",
        ".who{font-weight:600;margin-bottom:8px}.n{color:#6b7280;font-weight:400}",
        ".q{color:#9ecbff}.a{color:#a7f3a0}.t{color:#6b7280;font-size:12px}",
        "</style>",
        "<h1>%s</h1>" % T["title"],
        "<div class='sub'>%s %s · %d %s · %s %s</div>" % (
            time.strftime("%Y-%m-%d %H:%M"), T["today"], len(by), T["chat"],
            T["total"], len(data)),
    ]
    if not data:
        parts.append("<div class='card'>%s</div>" % T["none"])
    for name, items in by.items():
        parts.append("<div class='card'><div class='who'>%s <span class='n'>%d %s</span></div>"
                     % (e(name), len(items), T["cnt"]))
        for ts, q, a in items[:6]:
            parts.append("<div class='t'>%s</div>" % time.strftime("%m-%d %H:%M", time.localtime(ts)))
            parts.append("<div class='q'>%s\uff1a%s</div>" % (T["ask"], e((q or "-")[:120])))
            parts.append("<div class='a'>%s\uff1a%s</div>" % (T["ans"], e((a or "-")[:120])))
        parts.append("</div>")
    with io.open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print("saved:", out, "(%d chats, %d rows)" % (len(by), len(data)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=1)
    ap.add_argument("--html", default=None)
    a = ap.parse_args()
    since = time.time() - a.days * 86400
    if a.html:
        html_report(since, a.html)
    else:
        text_report(since)


if __name__ == "__main__":
    main()
