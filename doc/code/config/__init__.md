# config/ — 配置域包

> **源码路径**: `backend/packages/harness/workagentharness/config/`
> **对应功能**: WAH-RUN-001 配置加载与校验

## 包职责

YAML 配置文件加载、环境变量展开、字段校验，输出类型安全的 `ChatModelConfig`。

## 文件清单

| 文件 | 职责 |
|---|---|
| `model_config.py` | `ChatModelConfig` frozen dataclass，模型配置的最小契约 |
| `loader.py` | YAML 加载、环境变量展开、字段校验入口 |
