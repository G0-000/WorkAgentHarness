# models/credential_loader.py — 凭证加载与脱敏

> **源码路径**: `backend/packages/harness/workagentharness/models/credential_loader.py`
> **对应功能**: WAH-RUN-002

## 顺序执行链

```text
resolve_api_key(config)
  │
  ├─► 环境变量 WORKAGENT_MODEL_API_KEY 非空 → 返回该值
  └─► 否则 → 返回 config.api_key（loader 已展开 ${ENV} 后的值）

mask_api_key(key)
  │
  ├─► 空 → ""
  ├─► 长度 ≤ 8 → 全 * 号
  └─► 否则 → 前 4 位 + **** + 后 4 位

sanitize_error(message)
  │
  └─► 把消息中的 sk-... 疑似密钥替换为 [REDACTED]
```

## 关键设计

1. **密钥只走环境变量**：`config.yaml` 里写 `${WORKAGENT_MODEL_API_KEY}`，loader 展开时缺变量直接报错，杜绝明文密钥入库。
2. **脱敏三件套**：`mask_api_key` 用于展示，`sanitize_error` 用于异常消息，双保险防止密钥进日志/终端。
3. **对应 EvoFlow**：`credential_loader.py` + `credential_sanitize.py` 的简化版，只保留本项目需要的两个函数。

## 边界与待补

- 无 CLI 认证文件加载（Claude Code / Codex auth.json）
- 无凭证池 / 多密钥轮换
- `sanitize_error` 只匹配 `sk-` 前缀，其他格式密钥不覆盖
