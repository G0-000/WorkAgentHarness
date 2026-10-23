# config/loader.py — 配置加载器

> **源码路径**: `backend/packages/harness/workagentharness/config/loader.py`
> **对应功能**: WAH-RUN-001

## 职责

读取 YAML 配置文件，递归展开 `${ENV_VAR}` 环境变量，做基本字段校验，返回 `ChatModelConfig`。

## 顺序执行链

```text
load_chat_model_config(path)
  │
  ▼ 1. 存在性检查
  ├─► Path.is_file() → 不存在抛 FileNotFoundError
  │
  ▼ 2. YAML 解析
  ├─► yaml.safe_load() → 顶层必须是 dict
  │
  ▼ 3. 取 models.chat
  ├─► raw.get("models", {}).get("chat", {})
  ├─► chat 必须是 dict
  │
  ▼ 4. 环境变量展开
  ├─► _expand_env(chat) 递归遍历 dict / list / str
  ├─► 仅当整个字符串匹配 ^\$\{([A-Z0-9_]+)\}$ 时展开
  │   └─► os.environ.get(name) → 不存在则报错
  │
  ▼ 5. 构造 dataclass
  ├─► ChatModelConfig(**chat) → TypeError 则字段无效
  │
  ▼ 6. 业务校验
  ├─► provider / model 不能为空
  ├─► openai-compatible 必须有 api_key
  └─► temperature ∈ [0, 2]
  │
  ▼ 返回 ChatModelConfig
```

## 关键设计

1. **独占式 env 展开**：`${KEY}` 单独占整个值才展开；`prefix_${KEY}` 不展开。避免半展开歧义。
2. **frozen dataclass**：配置加载后不可变。
3. **只校验 models.chat**：其他配置域后续补。

## 边界与待补

- 无默认配置文件路径搜索（必须显式传 path）
- 无配置热更新 / reload
- 无多环境 profile（dev / prod）
- 无 JSON Schema 自动生成
