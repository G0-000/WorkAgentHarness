# M8 — Web、桌面端与产品界面

> 本章的实现目标是 WorkAgentHarness。文中出现的 AgentFlow 路径、状态和第一次学习记录均为历史对照；WorkAgentHarness 当前状态以本仓库和 02 全量功能矩阵为准。

## 本章目标

把后端能力变成完整用户界面。学习 API contract、登录与权限状态、聊天流、thread 历史、模型/工具/知识/任务管理、React 状态和错误体验，并追 EvoFlow zcode/Tauri 桌面体系。

## 阅读入口

> **路径约定**：EvoFlow 核心表项中的 `evoflow/...` 相对 `backend/packages/harness/`；AgentFlow 第一版中的 `agentflow/...` 相对同仓库的 `backend/packages/harness/`。以 `backend/...` 或 `evopanel/...` 开头的路径相对各仓库根目录。

| 子系统 | EvoFlow | AgentFlow 第一版参考（WorkAgentHarness 映射见 02） |
|---|---|---|
| Web shell/router | `evopanel/src/`、pages、boot | `evopanel/src/main.js`、pages、lib |
| Chat | `src/react/ChatApp.tsx`、`react/chat-app/`、components/hooks/stores | `pages/chat-react.js`、`lib/api-client.js` |
| zcode stack | `evopanel/src/zcode-ui/`、`evopanel/src/zcode-services/`、`evopanel/src/zcode-shared/`、`evopanel/src/zcode-rpc/`、`evopanel/src/zcode-provider/` | 需逐项盘点，初学版不是等价 stack |
| Backend contract | `backend/app/gateway/routers/`、v4/speech | `backend/app/gateway/routers/` |
| Desktop | Tauri shell/config/commands and IPC | 初学版浏览器界面；桌面端列为待实现范围 |

`zcode` 目录是当前源码体系的一部分，不称为历史命名；通过 package.json、imports、entry points 和实际调用确认各包用途。

## 四级学习

### 核心代码讲解清单

从 Vite boot/router 和页面 mount/unmount 讲到 `lib/api-client.js` 的 URL/auth/request/SSE parsing，再追聊天组件的 state/store、thread/history、tool event rendering 与模型页面表单。EvoFlow 侧按 `src/react/ChatApp.tsx`、hooks/store、`zcode-ui` 组件、`zcode-services` 后端能力、`zcode-shared` protocol、`zcode-rpc` 与 `zcode-provider` 的真实 imports 逐层讲解；桌面章节再追 Tauri command/IPC/权限边界。每处解释请求、状态更新、错误/取消和持久化。

### L1 入门闭环

启动 Vite 页面 → 调 API health/models → 输入一条消息 → 展示结果 → 显示网络错误。先用 fake API 和可控状态。

### L2 基础能力

补 API client、认证持久化/过期、SSE 增量和断流处理、创建/切换 thread、历史加载、loading/error/empty 状态、模型配置表单、表单校验、键盘可访问性和页面路由。

### L3 完整功能

以 EvoFlow UI 路由和产品菜单为清单，盘点所有页面、设置、对话、历史/分享、模型/provider、工具/plugins/MCP、知识/文件、subagents/tasks/collab、组织/权限、observability/eval、voice/speech、v4 protocol、Git/terminal/browser/workspace 等功能。然后梳理 zcode UI components、services、protocols、RPC 和 provider 分层；按用户旅程实现功能等价界面/API，不要求复制上游品牌素材或内部代码。

### L4 高级边界

验证刷新恢复、多个 tab/session、token 到期、错误重试、重复提交、长流取消、浏览器断线恢复、文件上传大小/权限、桌面 IPC 权限、系统密钥存储、自动更新/日志、Web 与桌面 API 差异、多语言和可访问性。

## 练习与验收

AgentFlow 第一版的 Archify 图（历史参考）：[M8 前端图](/Users/main/AgentFlow/doc/doc-dev/01-里程碑/diagrams/M8-frontend-20261011-034339/M8.html)。它展示精简 Web 初版，不能代表 EvoFlow 完整 Web/zcode/Tauri 产品面；完整 UI 功能矩阵完成后再更新目标图。

1. 做一张 UI action→API→权限→核心服务→storage→回显的映射表。
2. **JWT 受保护路由矩阵（§7 P1）**：逐个列出公开路由与受保护路由；对每个受保护路由验证无 token、格式错误、签名错误、过期 token、有效 token，以及适用时的权限不足主体。断言拒绝状态码/响应和允许范围，并验证 login/health 等明确公开的例外。签发 JWT 成功本身不算路由保护完成；AgentFlow 第一版当前 Gateway 路由尚未统一校验 JWT，此项须保持未完成，直到路由依赖/中间件真实接入并由集成测试覆盖。
3. **真实分块与历史恢复（§7 P1）**：分别验收流式和历史。用有延迟的 fake runner 逐块产出内容，断言客户端在 runner 完成前收到首个 delta、事件顺序和结束事件正确；再用浏览器发送多条消息、刷新页面并切换 thread，断言历史从后端持久层恢复且顺序/角色正确。另记录真实模型 provider 联调结果；若只有 fake runner 或 thread 壳没有消息历史，不能标成真实流式/历史恢复完成。
4. 通过浏览器验证模型设置、发送/取消和错误提示；对每类页面检查初始/空/加载/成功/失败/无权限状态。全链路声明中的每个用户旅程都要有对应 action→API→授权→服务→storage→UI 回显的端到端证据；无证据项从“已完成”说明中移除或标记未完成，并在 §5.3 收口复核。
5. 桌面能力单列：启动子进程、IPC 权限、文件路径、secret 存储、退出清理；不能只把 Web 页面嵌入壳就算桌面对齐。

## 深入链接

- 第一次学习记录：[M8 前端界面](/Users/main/AgentFlow/doc/doc-dev/01-里程碑/M8-前端界面.md)
- 代码说明：[API client](/Users/main/AgentFlow/doc/doc-code/evopanel/api-client.md)、[Chat UI](/Users/main/AgentFlow/doc/doc-code/evopanel/chat-react.md)、[models](/Users/main/AgentFlow/doc/doc-code/evopanel/models.md)、[login](/Users/main/AgentFlow/doc/doc-code/evopanel/login.md)
