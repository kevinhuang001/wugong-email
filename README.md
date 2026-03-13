# Wugong Email 🚀

Wugong Email 是一款为 AI 时代设计的**极简、高效、AI 友好**的命令行邮件管理器。它采用 TUI 界面，专为开发者和 AI 助手（如 Cursor, Trae）优化，让邮件处理像编写代码一样简单。

## ✨ 核心特性

- **OAuth2 全自动支持**：内置本地服务器，自动完成 Gmail、Outlook 等主流邮箱的 Token 交换与静默刷新，无需手动配置复杂参数。
- **极简端到端加密**：使用 PBKDF2 + Fernet 对配置文件进行端到端加密，确保本地账户信息安全，仅需一个主密码即可管理所有账号。
- **多账号无缝管理**：支持无限数量的邮件账号，内置 Gmail, Outlook, QQ, 163 等预设，支持一键切换与全局同步。
- **AI 友好设计**：结构化的 CLI 输出与极简的配置逻辑，极大方便 AI 助手进行邮件读取、搜索与自动化处理。

---

## 🛠️ 快速安装

### 🍎 macOS / 🐧 Linux
```bash
curl -sSL https://raw.githubusercontent.com/kevinhuang001/wugong-email/main/install.sh | bash
```

### 🪟 Windows (PowerShell)
```powershell
irm https://raw.githubusercontent.com/kevinhuang001/wugong-email/main/install.ps1 | iex
```

*安装完成后，请根据提示将 `~/.wugong` (Unix) 或 `%USERPROFILE%\.wugong` (Windows) 添加到 PATH 环境变量。*

---

## 🚀 快速上手

1. **初始化**：设置主密码与同步计划
   ```bash
   wugong init
   ```

2. **添加账号**：根据向导配置您的第一个邮箱
   ```bash
   wugong account add
   ```

3. **查看邮件**：
   ```bash
   wugong list
   ```

4. **同步邮件**：
   ```bash
   wugong sync
   ```

5. **阅读邮件**：
   ```bash
   wugong read -i <ID>
   ```

6. **发送邮件**：
   ```bash
   wugong send
   ```

---

## 💡 为什么选择 Wugong Email？

在 AI 辅助编程的今天，我们需要的不是臃肿的 GUI 客户端，而是一个能够被 AI 轻松理解、调用且足够安全的邮件工具。Wugong Email 剥离了所有冗余，只保留最核心的邮件处理能力，是您 AI 工作流中的完美一环。
