# -*- coding: utf-8 -*-
# ASCII-only source; Chinese via \uXXXX escapes. v6:
#  - parse "wxid_xxx:\n" prefix inside group content (sender + body)
#  - own-message detection via that prefix (sender_id is numeric in groups)
#  - per-group @-name candidates from self info + group members + config
import io, json, os, sys, time, urllib.request as u

_real_print = print

from wechatauto import WeChatDB, WeChatGUI, WxParam

try:
    import winsdk
except Exception:
    WxParam.ENABLE_OCR = False

# wechatauto/logger.py replaces sys.stdout with a block-buffered TextIOWrapper at
# import time, so print() never reaches a redirected log until exit. Undo that.
try:
    sys.stdout.reconfigure(line_buffering=True, write_through=True)
except Exception:
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                      errors="replace", line_buffering=True,
                                      write_through=True)
    except Exception:
        pass


def print(*a, **k):          # noqa: A001 - deliberate shadow, forces flush
    k.setdefault("flush", True)
    _real_print(*a, **k)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENVFILE = os.path.join(ROOT, "config.env")


def load_env_file(path=ENVFILE):
    """UTF-8 key=value config; overrides bat `set` so Chinese never enters a .bat."""
    try:
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()
    except Exception as e:
        print("[bot] env file skip: %r" % (e,))


load_env_file()


def env(k, d=""):
    return os.environ.get(k, d)


RAW = [w for w in env("WXAI_WATCH", "filehelper").split(",") if w.strip()]
MOCK = env("WXAI_MOCK") == "1"
DRY = env("WXAI_DRY") == "1"
RESOLVE = env("WXAI_RESOLVE", "1") == "1"
AT_ONLY = env("WXAI_AT_ONLY", "0") == "1"
AT_CFG = [x.strip() for x in env("WXAI_AT_NAME", "").split(",") if x.strip()]
HINT = env("WXAI_HINT", "")
SELF_CHATS = set(x for x in env("WXAI_SELF_CHATS", "filehelper").split(",") if x.strip())
MIN_GAP = float(env("WXAI_MIN_GAP", "8"))
AUTO = env("WXAI_AUTO_PRIVATE", "0") == "1"
MAX_PER_MIN = int(env("WXAI_MAX_REPLIES_PER_MIN", "10"))
ESC_ON = env("WXAI_ESCALATE", "1") == "1"
ESC_TO = env("WXAI_ESCALATE_TO", "filehelper")
DIGEST_AT = env("WXAI_DIGEST_AT", "")          # "21:00" -> daily at that local time
DIGEST_TO = env("WXAI_DIGEST_TO", "filehelper")
DIGEST_EVERY = float(env("WXAI_DIGEST_EVERY", "0"))     # seconds; 0 = off
LOGPATH = os.path.join(ROOT, "data", "chat_log.db")
try:
    os.makedirs(os.path.dirname(LOGPATH), exist_ok=True)
except Exception:
    pass
SKIP = tuple(x for x in env("WXAI_SKIP_PREFIX",
                            "gh_,newsapp,brandsessionholder,filehelper,fmessage,"
                            "medianote,floatbottle,qqmail,@openim,gamelife").split(",") if x)
PERSONA = env("WXAI_PERSONA", "\u4e2d\u6587\u53e3\u8bed\u5316\uff0c\u7b80\u77ed80\u5b57\u5185")
TEXT_TYPES = ("1", "text", "\u6587\u672c", "\u6587\u5b57")
VOICE_TYPES = ("34", "voice", "\u8bed\u97f3")
AT_ALL = "\u6240\u6709\u4eba"   # everyone-mention

T0 = time.time()


def step(msg):
    print("[bot] +%.1fs %s" % (time.time() - T0, msg))


step("open db")
_dbkw = {}
if env("WXAI_DB_DIR"):
    _dbkw["db_dir"] = env("WXAI_DB_DIR")
if env("WXAI_ACCOUNT"):
    _dbkw["account"] = env("WXAI_ACCOUNT")
db = WeChatDB(**_dbkw)
step("db ready")
info = db.get_self_info() or {}
step("self info ok")
me = str(info.get("username") or info.get("wxid") or info.get("user_name") or "")
nick = str(info.get("nick_name") or info.get("nickname") or "")
step("init gui")
gui = None if DRY else WeChatGUI()
step("gui ready")


def _conn():
    import sqlite3
    c = sqlite3.connect(LOGPATH, timeout=5)
    c.execute("CREATE TABLE IF NOT EXISTS chat_log("
              "id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, chat TEXT, "
              "who TEXT, user_text TEXT, ai_text TEXT)")
    c.commit()
    return c


def record(chat, who, user_text, ai_text):
    try:
        c = _conn()
        c.execute("INSERT INTO chat_log(ts,chat,who,user_text,ai_text) VALUES(?,?,?,?,?)",
                  (time.time(), chat, who, user_text, ai_text))
        c.commit()
        c.close()
    except Exception as e:
        print("[bot] record fail %r" % (e,))


def digest_text(since, limit=8):
    """Summarise replies since a timestamp, ready to send to yourself."""
    try:
        c = _conn()
        rows = c.execute(
            "SELECT chat, who, user_text, ai_text, ts FROM chat_log "
            "WHERE ts >= ? ORDER BY ts", (since,)).fetchall()
        c.close()
    except Exception as e:
        return "[bot] digest fail %r" % (e,)
    if not rows:
        return ""
    by = {}
    for chat, who, q, a, ts in rows:
        by.setdefault((chat, who), []).append((q, a, ts))
    span = int((time.time() - since) / 60)
    head = "[\u52a9\u624b\u6c47\u603b] \u8fc7\u53bb %d \u5206\u949f\uff0c%d \u4e2a\u4f1a\u8bdd\uff0c%d \u6761\u56de\u590d" % (
        span, len(by), len(rows))
    out = [head]
    for (chat, who), items in list(by.items())[:limit]:
        q, a, ts = items[-1]
        out.append("")
        out.append("\u2022 %s\uff08%d \u6761\uff09" % (who or chat, len(items)))
        out.append("  \u95ee\uff1a%s" % (q[:40] if q else "-"))
        out.append("  \u7b54\uff1a%s" % (a[:40] if a else "-"))
    if len(by) > limit:
        out.append("")
        out.append("...\u8fd8\u6709 %d \u4e2a\u4f1a\u8bdd\uff0c\u8be6\u89c1 tools\\report.html" % (len(by) - limit))
    return "\n".join(out)


def sessions(limit=300):
    try:
        return list(db.get_sessions(limit=limit) or [])
    except Exception:
        return []


def nickname(u):
    try:
        return str(db.get_nickname(u) or u)
    except Exception:
        return u


def resolve(w):
    """Only nickname-looking values need a lookup; wxid/@chatroom pass through.

    get_nickname opens contact.db per call, so never loop it over all sessions.
    """
    if not RESOLVE:
        return w
    if w.endswith("@chatroom") or w.startswith("wxid_") or w in ("filehelper", "newsapp"):
        return w
    try:
        for hit in db.search_contact(w) or []:
            u = hit.get("username") or hit.get("wxid")
            if u and (w == str(hit.get("nick_name") or "") or w == str(hit.get("remark") or "")):
                return str(u)
    except Exception:
        pass
    for s in sessions(60):
        u = str(s.get("username") or s.get("wxid") or "")
        if u == w:
            return u
    return w


step("resolve watch list")
WATCH = [resolve(w) for w in RAW]
step("watch resolved")


def at_names_for(g):
    names = set(AT_CFG)
    if nick:
        names.add(nick)
    try:
        for m in db.get_group_members(g) or []:
            if str(m.get("username") or "") == me:
                for k in ("remark", "nick_name", "display_name"):
                    v = m.get(k)
                    if v:
                        names.add(str(v))
    except Exception:
        pass
    names.discard("")
    return names


step("probe group at-names")
GROUP_AT = {g: at_names_for(g) for g in WATCH if g.endswith("@chatroom")}


def eligible(u):
    """private chats only; skip official accounts / system accounts."""
    if not u or u.endswith("@chatroom"):
        return False
    if u in SELF_CHATS:
        return False
    for x in SKIP:
        if u == x or u.startswith(x) or u.endswith(x):
            return False
    return True


def build_targets():
    """WATCH always wins; AUTO adds every private chat that has unread messages."""
    out = list(WATCH)
    if AUTO:
        try:
            for s in sessions(150):
                u = str(s.get("username") or "")
                if eligible(u) and int(s.get("unread") or 0) > 0 and u not in out:
                    out.append(u)
        except Exception as e:
            print("[bot] session scan fail %r" % (e,))
    return out
step("group at-names ready")
top = {c: None for c in WATCH}
sent_text = {}
last_sent = {}


def istype(m, names):
    t = m.get("type")
    if isinstance(t, int):
        return str(t) in names
    return str(t) in names


def istext(m):
    return istype(m, TEXT_TYPES)


def isvoice(m):
    return istype(m, VOICE_TYPES)


def seq(m):
    try:
        return int(m.get("sort_seq") or m.get("local_id") or 0)
    except Exception:
        return 0


def split_prefix(t):
    """group content looks like 'wxid_xxx:\\nbody' -> (sender, body)."""
    i = t.find(":\n")
    if 0 < i < 64:
        head = t[:i]
        if head.startswith("wxid_") or head.endswith("@chatroom") or head.isalnum():
            return head, t[i + 2:]
    return "", t


def echo(c, t):
    now = time.time()
    lst = [(x, ts) for x, ts in sent_text.get(c, []) if now - ts < 180]
    sent_text[c] = lst
    return any(x == t for x, ts in lst)


def mentioned(c, body):
    if not c.endswith("@chatroom"):
        return True
    if "@" not in body:
        return False
    if AT_ALL in body:            # everyone-mention is not "me"
        return False
    for n in GROUP_AT.get(c, ()):
        if ("@" + n) in body or (n and n in body):
            return True
    return False


def ask(t):
    if MOCK:
        return "\u6536\u5230\uff0c\u6211\u8bb0\u4e0b\u4e86\u3002"
    key = os.environ["OPENAI_API_KEY"]
    base = env("WXAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    sys_prompt = PERSONA + (
        "\n\u5982\u679c\u4f60\u4e0d\u786e\u5b9a\u3001\u6216\u9700\u8981\u8001\u677f"
        "\u786e\u8ba4\uff08\u4ef7\u683c/\u5e93\u5b58/\u627f\u8bfa\uff09\uff0c"
        "\u8bf7\u5728\u56de\u590d\u672b\u5c3e\u52a0 [[NEED]]")
    body = {"model": env("WXAI_MODEL", "gpt-4o-mini"),
            "messages": [{"role": "system", "content": sys_prompt},
                         {"role": "user", "content": t}]}
    req = u.Request(base + "/chat/completions", data=json.dumps(body).encode(),
                    headers={"Content-Type": "application/json",
                             "Authorization": "Bearer " + key})
    return json.loads(u.urlopen(req, timeout=45).read())["choices"][0]["message"]["content"].strip()


def next_fire(base):
    if DIGEST_AT:
        try:
            hh, mm = DIGEST_AT.split(":")
            t = time.localtime(base)
            cand = time.mktime((t.tm_year, t.tm_mon, t.tm_mday,
                                int(hh), int(mm), 0, 0, 0, -1))
            while cand <= base:
                cand += 86400
            return cand
        except Exception as e:
            print("[bot] bad WXAI_DIGEST_AT %r: %r" % (DIGEST_AT, e))
    if DIGEST_EVERY > 0:
        return base + DIGEST_EVERY
    return 0


global_sent = []


def rate_ok():
    now = time.time()
    global_sent[:] = [t for t in global_sent if now - t < 60]
    return len(global_sent) < MAX_PER_MIN


def send(c, a):
    last_sent[c] = time.time()
    global_sent.append(time.time())
    if DRY:
        print("[bot] (dry) >> %s" % a[:50])
        return
    try:
        gui.send_msg(a, who=c)
        sent_text.setdefault(c, []).append((a, time.time()))
        print("[bot] >> %s" % a[:50])
    except Exception as e:
        print("[bot] send fail %r" % (e,))


_last_digest = [time.time()]
_next_digest = [next_fire(time.time())]

print("[bot] v9 watch=%s auto=%s mock=%s dry=%s at_only=%s esc=%s digest_at=%s every=%ss "
      "me=%s nick=%s"
      % (WATCH, AUTO, MOCK, DRY, AT_ONLY, ESC_ON, DIGEST_AT or "-", DIGEST_EVERY,
         me or "?", nick or "?"))
for g, names in GROUP_AT.items():
    print("[bot] %s at_names=%s" % (g, sorted(names)))

while True:
    TARGETS = build_targets()
    for c in TARGETS:
        try:
            ms = list(db.get_messages(c, limit=20) or [])
        except Exception as e:
            print("[bot] read fail %r" % (e,))
            continue
        if not ms:
            continue
        hi = max([seq(m) for m in ms] + [top.get(c) or 0])
        if top.get(c) is None:
            top[c] = hi
            print("[bot] %s baseline %d msgs" % (c, len(ms)))
            continue
        fresh = [m for m in ms if seq(m) > (top.get(c) or 0)]
        top[c] = hi
        for m in sorted(fresh, key=seq):
            raw = str(m.get("content") or "").strip()
            if not raw:
                continue
            sender, body = split_prefix(raw)
            if c in SELF_CHATS:
                print("[bot] skip self-chat %s: %s" % (c, body[:30]))
                continue
            if sender and me and sender == me:
                print("[bot] skip own msg: %s" % body[:30])
                continue
            if echo(c, body):
                print("[bot] skip echo: %s" % body[:30])
                continue
            if istext(m) and AT_ONLY and not mentioned(c, body):
                print("[bot] skip not-mentioned: %s" % body[:30])
                continue
            if time.time() - last_sent.get(c, 0) < MIN_GAP:
                print("[bot] skip rate-limit: %s" % body[:30])
                continue
            if not rate_ok():
                print("[bot] skip global-rate (%d/min): %s" % (MAX_PER_MIN, body[:30]))
                continue

            if istext(m):
                clean = body
                for n in GROUP_AT.get(c, ()):
                    clean = clean.replace("@" + n + "\u2005", "").replace("@" + n + " ", "")
                    clean = clean.replace("@" + n, "")
                clean = clean.strip()
                if not clean:
                    continue
                print("[bot] << %s: %s" % (c, clean[:40]))
                try:
                    a = ask(clean)
                except Exception as e:
                    print("[bot] model fail %r" % (e,))
                    continue
                need = "[[NEED]]" in a
                if need:
                    a = a.replace("[[NEED]]", "").strip()
                time.sleep(1.5)
                send(c, a)
                record(c, nickname(c), clean, a)
                if need and ESC_ON:
                    try:
                        gui.send_msg("[\u9700\u8981\u4f60\u63a5\u624b] %s\n\u95ee\uff1a%s\n"
                                     "AI \u5df2\u56de\uff1a%s" % (nickname(c), clean[:60], a[:60]),
                                     who=ESC_TO)
                        print("[bot] escalate -> %s" % ESC_TO)
                    except Exception as e:
                        print("[bot] escalate fail %r" % (e,))
            elif isvoice(m) and HINT:
                print("[bot] << voice from %s" % c)
                send(c, HINT)
            else:
                print("[bot] skip non-text (%s): %s" % (m.get("type"), c))
    if _next_digest[0] and time.time() >= _next_digest[0]:
        try:
            txt = digest_text(_last_digest[0])
            if txt:
                gui.send_msg(txt, who=DIGEST_TO)
                print("[bot] digest sent to %s (%d chars)" % (DIGEST_TO, len(txt)))
            else:
                print("[bot] digest skipped (no traffic)")
        except Exception as e:
            print("[bot] digest fail %r" % (e,))
        _last_digest[0] = time.time()
        _next_digest[0] = next_fire(time.time())
    time.sleep(2)
