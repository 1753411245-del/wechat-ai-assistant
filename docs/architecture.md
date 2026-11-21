# 架构与关键实现

## 数据流

```
              ┌───────────────────────────────────────────┐
              │  微信 4.x 客户端（Weixin.exe，已登录）      │
              │   xwechat_files/.../db_storage/*.db       │
              └───────────────┬───────────────────────────┘
                              │ 只读解密（wechatauto-replica）
                              ▼
  ┌──────────────────────────────────────────────────────────┐
  │ src/wxa.py 主循环（每 2 秒）                               │
  │  1. 构建目标列表：WATCH（白名单）+ AUTO_PRIVATE（所有私聊） │
  │  2. 逐会话 get_messages → 按 sort_seq 取名次增量            │
  │  3. 过滤：自聊 / 自己发的 / 回音 / 频率 / 群 @ 判定          │
  │  4. 清洗群消息前缀与 @ 文本 → 送模型                        │
  │  5. UIA 发送 → 记录 sent_text / 落库 chat_log               │
  └──────────┬───────────────────────────┬───────────────────┘
             │                           │
             ▼                           ▼
   data/chat_log.db               文件传输助手（提醒 / 汇总）
             │
             ├─→ src/report.py（网页看板）
             └─→ src/export_xlsx.py（Excel）
```

## 六个不得不这么写的点（都是踩出来的）

1. **`type` 是中文名字符串**
   `wechatauto` 返回的行里 `type` 是 `文本 / 图片 / 语音 …` 而不是数字，
   直接 `int(type)` 会 `ValueError`。

2. **`local_id` 不能当水位线**
   文档明确：`local_id` 只在单个分片（`message_*.db`）内唯一，跨分片会重复。
   水位线必须用 `sort_seq`。

3. **群消息的正文带发送者前缀**
   群消息 `content` 形如 `wxid_xxx:\n正文`，且 `sender_id` 是**数字**（不是 wxid）。
   所以"是不是自己发的"只能靠解析前缀判断。

4. **自己的回复会回流**
   发出的消息会写进同一个库，若不拦就会自激刷屏。四道闸：
   `SELF_CHATS` 跳过 / 前缀等于自己 wxid / 回音 180s / 每会话最小间隔。

5. **群里 @ 的昵称 ≠ 账号昵称**
   `@助理\u2005说话`：`助理` 是你在该群的昵称。程序从
   `get_group_members()` 的 remark 里猜，猜不到就用 `WXAI_AT_NAME` 手填。

6. **第三方包把 `sys.stdout` 换成了块缓冲**
   `wechatauto/logger.py` 在 import 时执行
   `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, ...)`，没开 `write_through`，
   于是 `print()` 在进程退出前不会落盘（日志里只有它自己的 stderr）。
   解决办法：`sys.stdout.reconfigure(line_buffering=True, write_through=True)` + `print(..., flush=True)`。

## 状态与持久化

| 数据 | 位置 | 说明 |
|---|---|---|
| 会话水位线 | 内存 `top[chat]` | 进程重启后第一次读取会重建基线（不回历史） |
| 回音窗口 | 内存 `sent_text[chat]` | 180 秒内相同内容不重复回 |
| 频率 | 内存 `last_sent` / `global_sent` | 每分钟上限 |
| 对话记录 | `data/chat_log.db` | 表 `chat_log(ts, chat, who, user_text, ai_text)` |

## 发送路径

`WeChatGUI.send_msg(text, who=...)`：
- 通过 UIA 找到主窗口 → 打开目标会话 → 剪贴板写入 → `Ctrl+V` → 回车
- **必须有交互式桌面**：SSH 会话 / Windows 服务 / 锁屏状态下会失败
- 首次发送前会做一次布局校准（日志里有 `已加载布局校准（wide）`）

## 多账号

`WeChatDB(db_dir=..., account=...)`；`list_accounts()` 可枚举数据目录下的所有账号。
配置里用 `WXAI_DB_DIR` / `WXAI_ACCOUNT` 指定，`src/setup.py` 会自动列出并写回。
