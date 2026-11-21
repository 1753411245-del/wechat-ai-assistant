# -*- coding: utf-8 -*-
"""把 chat_log.db 导成 Excel（没有 openpyxl 就退化成 CSV，Excel 也能打开）。"""
import io, os, sqlite3, sys, time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "chat_log.db")
OUT_XLSX = os.path.join(ROOT, "data", "chat_log.xlsx")
OUT_CSV = os.path.join(ROOT, "data", "chat_log.csv")

HEAD = ["\u65f6\u95f4", "\u4f1a\u8bdd", "\u6635\u79f0", "\u5bf9\u65b9\u8bf4", "AI \u56de\u590d"]


def load(days):
    if not os.path.exists(DB):
        return []
    c = sqlite3.connect(DB)
    try:
        rows = c.execute("SELECT ts, chat, who, user_text, ai_text FROM chat_log "
                         "WHERE ts >= ? ORDER BY ts", (time.time() - days * 86400,)).fetchall()
    except sqlite3.OperationalError:
        rows = []
    finally:
        c.close()
    return [(datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"), chat, who or chat, q or "", a or "")
            for ts, chat, who, q, a in rows]


def main():
    days = float(sys.argv[1]) if len(sys.argv) > 1 else 30
    rows = load(days)
    if not rows:
        print("no records in last %s days" % days)
        return 1
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except ImportError:
        with io.open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
            f.write(",".join(HEAD) + "\n")
            for r in rows:
                f.write(",".join('"%s"' % str(x).replace('"', '""') for x in r) + "\n")
        print("openpyxl not installed -> CSV:", OUT_CSV, "(%d rows)" % len(rows))
        return 0

    wb = Workbook()
    ws = wb.active
    ws.title = "chat_log"
    ws.append(HEAD)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for r in rows:
        ws.append(list(r))
    widths = [20, 26, 18, 60, 60]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w
    ws.freeze_panes = "A2"
    wb.save(OUT_XLSX)
    print("saved:", OUT_XLSX, "(%d rows)" % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
