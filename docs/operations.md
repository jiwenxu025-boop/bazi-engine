# 生产运维

本项目的运行数据位于 `/opt/bazi/data/`。该目录包含反馈、配额和生成指标，必须保留在版本控制之外。

## 首次部署

1. 在服务器创建受限权限的环境文件：`/opt/bazi/.env`，并执行 `chmod 600 /opt/bazi/.env`。
2. 以 [`.env.example`](../.env.example) 为字段清单填入生产值。不要把密钥写入命令行、仓库或聊天记录。
3. 确认 `bazi.service` 的 `EnvironmentFile` 指向 `/opt/bazi/.env`，运行用户拥有 `/opt/bazi/data/` 的读写权限。
4. 启动服务后检查服务器内网和公网的 `/api/health`。健康响应中的 `ai_enabled` 只表示 AI 功能开关，不暴露凭证。

## 常规发布

1. 在本地完成测试、静态检查和提交推送。
2. 在服务器执行 `git pull --ff-only`，不要删除或重建 `/opt/bazi/data/`。
3. 重启 `bazi.service`，等待服务就绪后检查 `systemctl is-active bazi.service` 与 `/api/health`。
4. 对涉及前端的改动，在桌面和移动视口各做一次浏览器验证。

## 回滚

通过 GitHub 对有问题的提交执行 revert，再按常规发布流程部署 `main`。不要在生产机上通过强制重置 Git 历史回滚，以免丢失未同步的运行状态。

## 备份

每日将 `/opt/bazi/data/` 归档到仓库外的受限目录或对象存储，并定期演练还原。备份应加密并设置保留期，因为反馈与运行指标虽然不含报告正文，仍属于运营数据。

运行中的 SQLite 数据库不能直接用文件复制代替在线备份。使用内置工具创建一致快照，再执行完整性检查：

```bash
cd /opt/bazi
./venv/bin/python -c "from pathlib import Path; from bazi_engine.runtime_backup import backup_runtime_database; backup_runtime_database(Path('data/runtime.sqlite3'), Path('/secure-backups/runtime.sqlite3'))"
./venv/bin/python -c "from pathlib import Path; from bazi_engine.runtime_backup import verify_runtime_database; verify_runtime_database(Path('/secure-backups/runtime.sqlite3'))"
```

恢复演练必须在临时目录完成：先校验备份，再以临时副本启动服务并核对关键表计数；不要直接覆盖 `/opt/bazi/data/runtime.sqlite3`。保留原 JSON/JSONL 文件至少一个发布周期，作为 SQLite 迁移后的回滚依据。

## 访问边界

- 管理汇总接口需要 `X-Admin-Key` 或 Bearer 管理密钥；不要为了排查问题临时关闭认证。
- 当前公网服务仅提供 HTTP。POST 可以避免把出生信息放进 URL，但不能提供传输加密。正式 HTTPS 上线应等待域名备案和证书配置完成。
