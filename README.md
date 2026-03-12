# 武功邮件 (Wugong Email) 🚀

一个极简、安全、基于 TUI 的命令行邮件管理器。支持多账号、OAuth2 自动授权、端到端加密存储以及强大的搜索功能。

## ✨ 特性

- **极简 TUI**：基于 `Rich` 和 `Questionary` 的精美终端界面。
- **多账号管理**：支持 Gmail, Outlook, QQ, 163 等主流服务商，支持设置“默认账号”。
- **安全第一**：支持 PBKDF2 + Fernet 对配置文件进行端到端加密。
- **OAuth2 自动化**：内置本地服务器自动换取 Access/Refresh Token，支持自动刷新，无感登录。
- **智能搜索**：支持关键字、发送者、日期范围的多重组合过滤。

---

## 🛠️ 安装

我们提供了自动化安装脚本，会自动处理 Python 环境检查、依赖安装及路径包装。

1. **执行安装**：
   ```bash
   bash install.sh
   ```
2. **配置环境变量**：
   安装完成后，将以下行添加到您的 `~/.zshrc` 或 `~/.bashrc` 中：
   ```bash
   export PATH="$PATH:$HOME/.wugong"
   ```
   然后执行 `source ~/.zshrc`。

---

## 🚀 快速上手

### 1. 配置账号 (Wizard)
运行配置向导，按照提示添加您的第一个邮箱。
```bash
wugong-wizard
```
*提示：您可以将第一个账号设为“默认账号”，之后使用 `list` 指令时无需再输入账号名。*

### 2. 查看邮件 (List)
- **查看默认账号**：
  ```bash
  wugong list
  ```
- **查看指定账号**：
  ```bash
  wugong list work
  ```

### 3. 阅读邮件 (Read)
使用 `list` 命令获取邮件 ID 后，可以使用 `read` 命令查看正文：
- **阅读指定账号的邮件**：
  ```bash
  wugong read -a outlook -i 1234
  ```
- **参数说明**：
  - `-a, --account`: 必填，账号友好名称。
  - `-i, --id`: 必填，邮件在 IMAP 服务器上的唯一 ID。

---

## 🔍 搜索与过滤 (并逻辑)

所有的检索参数都是 **AND (并)** 逻辑，即必须同时满足所有条件。

### 参数说明
- `-k, --keyword`: 在主题或正文中搜索关键字。
- `-f, --from-user`: 指定发送者（支持姓名或邮箱地址）。
- `--since`: 搜索该日期**之后**的邮件 (格式: `DD-Mon-YYYY`, 如 `01-Jan-2024`)。
- `--before`: 搜索该日期**之前**的邮件 (格式: `DD-Mon-YYYY`, 如 `31-Dec-2024`)。
- `-l, --limit`: 限制显示条数（默认 10 条）。

### 使用示例
- **搜索特定发送者的重要邮件**：
  ```bash
  wugong list -f "boss@company.com" -k "Report"
  ```
- **搜索今年以来的所有未读/已读邮件**：
  ```bash
  wugong list --since 01-Jan-2026
  ```
- **综合搜索（指定账号 + 关键字 + 时间范围）**：
  ```bash
  wugong list outlook -k "Invoice" --since 01-Mar-2026 --before 12-Mar-2026
  ```

---

## �️ 更新与卸载

我们在安装目录中提供了方便的脚本：

1. **更新 (Update)**：
   在源码仓库中运行 `./update.sh`。它会检查远程仓库是否有新的提交，在您确认后自动拉取并同步到安装目录。
   ```bash
   ./update.sh
   ```

2. **卸载 (Uninstall)**：
   运行 `./uninstall.sh`。它会删除安装目录 `~/.wugong` 和配置文件目录 `~/.config/wugong`。
   ```bash
   ./uninstall.sh
   ```

---

## �📂 目录结构
- **执行程序**: `~/.wugong/` (包含源码和虚拟环境)
- **配置文件**: `~/.config/wugong/config.toml` (支持 `WUGONG_CONFIG` 环境变量覆盖)
