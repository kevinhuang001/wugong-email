# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-03-13

### Features
- **AI 时代的原生支持**：极简的 CLI 设计与结构化输出，专为 OpenClaw 等自主 AI 智能体优化。
- **全自动 OAuth2**：支持 Gmail, Outlook 等主流邮箱的自动授权与静默刷新。
- **端到端加密存储**：使用 PBKDF2 + Fernet 加密配置文件，保障多账号信息安全。
- **多账号管理**：支持无限账号添加，内置主流服务商配置，支持默认账号一键操作。
- **高性能同步**：基于 IMAP UID 的增量同步，支持全量元数据同步与按需读取邮件正文。
- **跨平台支持**：提供 macOS, Linux, Windows 的一键安装脚本与环境自动配置。
- **智能搜索与列表**：支持按关键字、发送者、日期范围的多重过滤搜索。
- **后台自动任务**：支持一键开启 Cron (Unix) 或任务计划程序 (Windows) 实现后台自动同步。
