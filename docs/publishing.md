# 发布到 GitHub

## 1. 建仓库

打开 https://github.com/new ，填名称（如 `wechat-ai-assistant`），
**不要**勾选 "Add a README / .gitignore / license"（本地已有），创建。

## 2. 本地提交并推送

在这个目录里执行（把 URL 换成你的）：

```bash
git init
git add .
git commit -m "feat: 微信 4.x AI 自动回复（读库 + UIA，含看板与汇总）"
git branch -M main
git remote add origin https://github.com/<你的用户名>/wechat-ai-assistant.git
git push -u origin main
```

## 3. 发布前自查（重要）

```bash
git status --short          # 确认 config.env / data / logs 没有被加入
git grep -n "sk-"           # 不应有任何 API Key
git grep -n "wxid_"         # 不应有真实联系人 wxid
```

`.gitignore` 已排除：`.venv/`、`config.env`、`data/`、`logs/`、`*.db`、`*.log`。

## 4. 加分项（可选）

- **Releases**：打 tag `v1.0.0`，附上 `wechat-ai-assistant.zip` 方便别人下载
- **Issues 模板**：让使用者提供 `logs/run.log` 片段和微信版本号
- **README 截图**：`report.bat` 生成的看板截图放进去，转化率高
- **Topics**：`wechat` `wechat-bot` `llm` `deepseek` `uiautomation` `automation`

## 5. 不要做的事

- 不要把 `config.env`、`data/chat_log.db`、`logs/` 提交上去（里面是真实聊天记录和 API Key）
- 不要把 `wechatauto-replica` 的代码复制进仓库（它是第三方项目，用 pip 安装即可）
