# 微信 AI 助手（Windows / 微信 4.x）

> 用本地数据库读消息 + UIA 驱动窗口发送，给你的个人微信接上大模型：
> 自动回复私聊和新加好友、群里 @ 才回、需要你拍板的事单独提醒、每天汇总、网页看板和 Excel 导出。

**关键词**：微信 4.x · 自动回复 · DeepSeek / 任意 OpenAI 兼容模型 · 不注入进程 · 不需要降级微信

---

## 它能做什么

| 能力 | 说明 |
|---|---|
| 自动回复私聊 | 白名单或全自动（含新加好友） |
| 群消息 | 只在指定群里、且 @ 机器人才回（避免刷屏） |
| 语音/图片 | 收到语音自动回一句"打字说下"，不强行识别 |
| 人工接管 | 模型不确定（价格/库存/承诺）时，单独推一条提醒给你 |
| 每日汇总 | 每天固定时间把"跟谁聊了什么"发到你自己的文件传输助手 |
| 对话看板 | 双击 `report.bat` 打开网页，看当天每个会话的问答 |
| Excel 导出 | 双击 `export.bat` 导出 `data/chat_log.xlsx` |
| 常驻运行 | `service.bat` 崩溃自动重启，可放进启动目录开机自启 |

## 原理（为什么选这条路）

```
微信 4.x 客户端
   │ ① 读：解密 xwechat_files/.../db_storage 的 message_*.db / contact.db
   │ ② 写：Win32 UIA + 剪贴板驱动窗口，模拟人手发送
   ▼
src/wxa.py ── 轮询增量 / 判定规则 / 模型调用 / 防重复
   │
   ├─→ data/chat_log.db（每次回复落库）→ report.bat / export.bat
   └─→ 文件传输助手（实时提醒 + 每日汇总）
```

**本项目的选型依据**（都实测过，不是猜的）：

| 方案 | 结论 |
|---|---|
| wcferry（注入 SDK.dll） | ❌ 只支持微信 3.9.x；4.1 注入失败 `wcf.exe 退出码 4` |
| 降级微信到 3.9.x | ❌ 服务端拒绝登录（版本过低） |
| wxauto | ❌ PyPI 已下架（HTTP 404），且只支持 3.9 |
| **wechatauto-replica + 本项目** | ✅ 读库版本不敏感，发送走 UIA，4.1.12+ 可用 |

## 环境要求

- Windows 10 / 11（发送依赖 UIA，必须在有登录桌面的机器上跑）
- 微信 **4.1.12 及以上**，且已登录、窗口不锁屏不最小化
- Python **3.10+ 64 位**（3.13 也行，会自动关 OCR）

> 不注入进程、不改微信文件，风控压力比 hook 类方案小很多，但仍建议**先在小号上跑**。

## 三步开始

```bat
:: 1) 装依赖 + 生成配置（首次）
quickstart.bat

:: 2) 按提示选账号、选要接管的会话、填 API Key（写入 config.env）

:: 3) 日常启动（崩溃自动重启）
service.bat
```

停止：`stop.bat`　看板：`report.bat`　导表：`export.bat`

## 配置说明（`config.env`）

| 键 | 作用 |
|---|---|
| `WXAI_WATCH` | 白名单：私聊 wxid、群 `xxx@chatroom`，逗号分隔 |
| `WXAI_AUTO_PRIVATE` | 1=自动接管所有私聊（含新好友） |
| `WXAI_AT_ONLY` | 1=群里只回 @（**强烈建议开**） |
| `WXAI_AT_NAME` | 群里 @ 的昵称，多个逗号分隔；留空自动识别 |
| `WXAI_MIN_GAP` | 同一会话两次回复最小间隔（秒） |
| `WXAI_MAX_REPLIES_PER_MIN` | 全局每分钟上限（防失控） |
| `WXAI_SKIP_PREFIX` | 排除的会话前缀/后缀（公众号、系统号） |
| `WXAI_SKIP_CHATS` | 排除的会话 wxid（逗号分隔）：这些号**永远不私聊回复** |
| `WXAI_ESCALATE` / `_TO` | 人工接管提醒开关 / 推送到哪个会话 |
| `WXAI_DIGEST_AT` | 每天几点发汇总（`21:00`），留空用 `WXAI_DIGEST_EVERY` 按秒 |
| `WXAI_BASE_URL` / `WXAI_MODEL` / `OPENAI_API_KEY` | 模型（OpenAI 兼容：DeepSeek、通义、Moonshot、本地 Ollama 都行） |
| `WXAI_PERSONA` | 人设与话术边界 |
| `WXAI_DB_DIR` / `WXAI_ACCOUNT` | 多账号或自定义数据目录时指定 |

模型示例：

```ini
# DeepSeek
WXAI_BASE_URL=https://api.deepseek.com/v1
WXAI_MODEL=deepseek-chat

# 通义千问（有免费额度）
WXAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
WXAI_MODEL=qwen-plus

# 本地 Ollama（免费、离线）
WXAI_BASE_URL=http://localhost:11434/v1
WXAI_MODEL=qwen2.5:7b
OPENAI_API_KEY=ollama
```

## 换一个微信号 / 多账号

- **换账号**：直接跑 `python src/setup.py`，重新生成 `config.env` 即可（不写死任何账号信息）
- **一台电脑多个微信账号**：`WeChatDB` 支持按账号读，向导里会列出检测到的账号让你选，写入 `WXAI_ACCOUNT`
- **自定义数据目录**：`WXAI_DB_DIR=D:\WeChatData`

## 目录结构

```
quickstart.bat        首次安装 + 配置向导
service.bat           日常启动（崩溃自动重启）
stop.bat / report.bat / export.bat
scripts/findpy.bat    自动定位 64 位 Python
src/wxa.py            主程序：收 → 判定 → 模型 → 发 → 落库
src/setup.py          交互式配置向导
src/report.py         网页看板 / 文本摘要
src/export_xlsx.py    Excel 导出
src/list_chats.py     列会话（查 wxid）
src/peek.py           看某会话原始消息（调试群 @ 格式）
src/check_running.ps1 防重复启动
config.env            你的配置（已 gitignore）
data/chat_log.db      对话记录（已 gitignore）
logs/run.log          运行日志
docs/                 架构说明、FAQ、排错
```

## 常见问题

见 [docs/faq.md](docs/faq.md) 与 [docs/troubleshooting.md](docs/troubleshooting.md)。高频几条：

- **发送失败**：微信窗口被锁屏/最小化；恢复后自动恢复
- **群里不回**：检查 `WXAI_WATCH` 是否含该群、`WXAI_AT_NAME` 是否是你在该群的昵称（用 `src/peek.py` 看真实 @ 格式）
- **新好友不回**：`WXAI_AUTO_PRIVATE=1`，且该会话不在 `WXAI_SKIP_PREFIX` 里
- **重复回复**：程序已有 4 道防重闸（自己发的/回音/间隔/全局限速），若仍出现请附 `logs/run.log`

## 已知限制

- 只能在 Windows 上跑；发送必须有人登录的桌面会话（SSH / 服务方式跑发送会失败）
- 锁屏、最小化、远程桌面断开时发送失败（收消息不受影响）
- 语音不做 ASR（只回提示）；要转文字需自行接讯飞/Whisper
- 微信界面大改版可能导致 UIA 锚点失效，需要更新 `wechatauto-replica`

## 免责声明

本项目仅用于个人自动化与技术研究，请遵守微信用户协议与当地法律。
因使用本项目导致的账号限制、数据丢失或其它后果由使用者自行承担。
建议只在自己的账号上试用，不要用于群发、营销骚扰或任何违规用途。

## License

MIT
