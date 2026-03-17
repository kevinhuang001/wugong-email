# Wugong Email Agent Skill Guide

本指南旨在指导智能体（Agent）如何高效、正确地操作 Wugong Email CLI 工具。

## 1. 执行策略 (Execution Strategy)

### 非交互模式 (Standard Commands)
除了 OAuth2 登录外，**所有** CLI 命令都必须附加以下全局参数，以确保输出可解析且执行不中断：
- `--json`: 强制输出标准化的 JSON 格式结果。
- `--non-interactive`: 禁用所有交互式提示。

### OAuth2 登录 (OAuth2 Authentication)
当 `--login-method` 为 `OAuth2` 时，必须采用**交互式**方式执行：
1. **不要**添加 `--non-interactive`。
2. **告知用户**：系统将弹出一个浏览器 URL，请用户完成授权。
3. **流程**：智能体执行命令 -> 获取输出中的 URL -> 告知用户 -> 等待用户在浏览器操作成功 -> 智能体继续后续操作。

## 2. CLI 命令教程 (CLI Usage)

### 全局参数
- `-p` 或 `--encryption-password`: 指定加密密码。
- `-L` 或 `--log-level`: 设置日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)。

### 加密密码 (-p <password>)
- **必须提供的情况**: 仅当用户在初始化时开启了加密功能（`encryption_enabled` 或 `encrypt_emails` 为 `true`）时，非交互模式下的所有涉及敏感数据的命令（如 `init`, `account add`, `sync`, `read`, `send` 等）才必须提供 `-p <password>`。
- **无需提供的情况**: 如果用户选择了不开启加密（使用 `--no-encrypt-creds --no-encrypt-emails`），则所有命令均无需携带 `-p` 参数。

### 常用命令示例
- **初始化 (不开启加密)**: `wugong init --no-encrypt-creds --no-encrypt-emails --sync-interval 10 --non-interactive --json`
- **初始化 (开启加密)**: `wugong init --sync-interval 10 --non-interactive -p <password> --json`
- **列表账户**: `wugong account list --non-interactive --json` (注：若开启了加密且需查看详细统计信息，可能需要携带 `-p`)
- **同步邮件 (加密状态)**: `wugong sync --non-interactive -p <password> --json`
- **同步邮件 (非加密状态)**: `wugong sync --non-interactive --json`
- **读取邮件**: `wugong read -a <account> -i <index> --non-interactive -p <password> --json` (注：解密邮件内容必须提供密码)

## 3. 决策流程 (Decision Flow)

智能体在接收到用户指令后，应遵循以下逻辑判断：

### 第一步：检查安装状态
- **检查方法**: 查看 `~/.config/wugong/config.toml` 是否存在。
- **如果未安装**:
    1. **执行安装**: 运行安装脚本 `curl -sSL https://raw.githubusercontent.com/kevinhuang001/wugong-email/main/install.sh | bash`。
    2. **询问用户配置**:
        - 是否开启加密？
        - 设置加密密码是什么？
        - 需要添加的初始账户信息（名称、提供商、邮箱、密码等）。
    3. **执行初始化**: 使用用户提供的信息运行 `wugong init`。
    4. **添加账户**: 运行 `wugong account add`。
- **如果已安装**:
    - 继续下一步。

### 第二步：检查账户状态
- **执行命令**: `wugong account list --json`。
- **判断逻辑**:
    - 如果用户要求的账户已存在：直接执行目标操作。
    - 如果账户不存在：询问用户账户信息并执行 `wugong account add` 后再操作。

### 第三步：执行目标操作
- 根据用户具体需求（读信、写信、同步等），构建带 `--json` 和 `--non-interactive` 的命令并执行。

## 4. 最佳实践
- **安全性**: 优先从环境变量 `WUGONG_PASSWORD` 读取密码，或者在命令中使用 `-p` 传递。
- **错误处理**: 始终解析 JSON 输出中的 `status` 字段。如果为 `error`，请根据 `message` 告知用户失败原因。
- **环境适配**: 优先使用安装后的 `wugong` 别名，如果环境未配置别名，则使用 `python3 main.py`。
