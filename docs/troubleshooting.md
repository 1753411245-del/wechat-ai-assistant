# 排错手册

## 先看两个地方

1. `logs/run.log` —— 主程序日志，每步都带 `[bot] +Xs` 打点
2. `logs/report.txt` / `report.bat` —— 有记录说明发送链路是通的

## 症状对照

| 现象 | 原因 | 处理 |
|---|---|---|
| 启动后没有任何 `[bot]` 行 | 第三方包替换了 `sys.stdout`（块缓冲） | 本项目已修：`reconfigure(write_through=True)`；确认用的是最新 `src/wxa.py` |
| 卡在 `+Xs open db` | 微信未登录 / 数据目录不对 | 确认微信已登录；必要时配 `WXAI_DB_DIR` |
| 卡在 `+Xs probe group at-names` | `get_group_members` 慢（大群/大 contact.db） | 把群从 `WXAI_WATCH` 移除，或直接用 `WXAI_AT_NAME` 手填 |
| 有 `<<` 没有 `>>` | 发送失败（窗口被挡/锁屏） | 恢复微信窗口、别锁屏；看日志里 `send fail` 的具体异常 |
| `send fail` 提到找不到控件 | UIA 锚点失效（微信改版） | 升级 `wechatauto-replica`；或调窗口尺寸后再试 |
| 群里不回 | 群不在 `WXAI_WATCH` / 没 @ / `AT_NAME` 不对 | `python src/peek.py <群id>` 看真实 @ 文本，把名字填进 `WXAI_AT_NAME` |
| 重复回复 | 多开了两个进程 | `stop.bat` 全停，再 `service.bat`；`check_running.ps1` 会阻止二次启动 |
| 回复内容很奇怪 | 人设不够具体 | 改 `WXAI_PERSONA`，写清语气、字数、能答什么不能答什么 |
| `model fail 401` | API Key 无效 | 重新生成 key |
| `model fail 402` | 余额不足 | 充值或用本地 Ollama |
| `model fail URLError` | 网络/代理问题 | DeepSeek 国内直连，别挂代理 |

## 常用命令

```bat
:: 看会话和 wxid
python src\list_chats.py

:: 看某个会话的原始消息（确认 @ 格式、自己发的消息长什么样）
python src\peek.py 12345678@chatroom 15

:: 重新生成配置
python src\setup.py

:: 干跑：只打印不发送（安全验证）
set WXAI_DRY=1
.venv\Scripts\python.exe -u src\wxa.py
```

## 日志里这几行代表什么

```
[bot] +0.6s gui ready                启动耗时，正常 < 5s
[bot] XXX baseline 20 msgs           首次读取只记基线，不回历史
[bot] << wxid: 你好                   收到新消息（群消息会剥掉前缀和 @）
[bot] >> 回复内容                     已发送
[bot] skip own msg / echo / not-mentioned / rate-limit   被规则拦截的原因
[bot] escalate -> filehelper         已推送"需要你接手"
[bot] digest sent to filehelper      定时汇总已发出
```
