# 第 3 章｜Agent 构建、角色与单轮执行

> 所属篇：启动一个可配置、可恢复的 Agent
> 功能范围：`WAH-RUN-003–004`
> 导航：[教程册总目录](../README.md) · [本篇导读](README.md) · [课程索引](../../学习手册/课程目录.md) · [功能路线](../../学习手册/功能单元路线.md) · [唯一状态清单](../../学习手册/功能清单.md)

## 本章要做出的东西
把模型变成真实用户请求能触发的 Agent：接收消息、构造角色与提示、执行模型、返回结果。此时不加入工具和复杂多 Agent 状态。

## 本章总流程与小节

本章沿“入口输入 → 角色/提示装配 → Agent graph → 模型调用 → 响应返回”追踪。章节正文是端到端总流程；具体功能如下：

| 小节 | 具体功能 | 代码入口 | 说明文档 |
|---|---|---|---|
| 第 1 节 | Agent 构造、角色与系统提示 | `agents/lead_agent/agent.py` | [如何把模型装配成一个 Agent](第03章-Agent构建角色与单轮执行/第01节-Agent构造与角色提示.md) |
| 第 2 节 | 单轮输入、调用和结果提取 | `agents/lead_agent/agent.py`、`execution/run_service.py` | [一条用户消息怎样走完执行链](第03章-Agent构建角色与单轮执行/第02节-单轮执行与结果返回.md) |

实际实现保存在 `backend/packages/harness/workagentharness/`；小节解释这些 `.py` 文件的调用关系，不复制第二份实现。

## EvoFlow 阅读顺序
1. 从 `backend/app/gateway/routers/chat_sessions.py` 找请求函数、schema、身份依赖和调用服务，记 session/thread 的创建时机。
2. 读 `agents/lead_agent/agent.py`：分开标注 Agent 构建与执行，圈出 model、system prompt、tools、middleware、checkpointer 的注入点。
3. 沿 `agents/lead_agent/prompt*.py` 看固定系统指令、角色配置、动态上下文如何合成。
4. 对照 `agents/goal/`、`agents/mission_state/`，说明它们与 lead agent 区别；本章只仿写单轮调用。
5. 从 route/service 跟到 invoke/stream，再追回 response/event。标出异常翻译、id 传递和权限检查。

## WorkAgentHarness 仿写顺序
1. 定义 `AgentInput` / `AgentResult`：用户文本、会话标识、角色/配置引用、结果文本和终态；核心层不依赖 HTTP Request。
2. 设计 Agent 构造层，注入上一章的模型接口；角色/提示配置与模型供应商配置分开。
3. 实现最短执行器：system prompt + user input → model → result，不接持久化与工具。
4. 接一个项目真实入口，由 adapter 把请求转成 `AgentInput`；route 负责协议而非 Agent 业务逻辑。
5. 增加 thread/session 标识，验证两条会话不会共享意外状态；记录哪些状态仍在内存。
6. 再加 stream 输出；复用同一构建和授权逻辑，对比流与非流的终态/错误。

## AgentFlow 第一遍复盘

阅读 `agents/lead_agent/agent.py` 中的 `make_lead_agent`，记录模型、tools、middleware、checkpointer 与 prompt 的实际装配参数；沿 AgentFlow 的 CLI/聊天入口确认它是否能被真实用户请求触发。把第一遍尚未实现的多角色、stream 和失败处理记为差异，不把“函数已存在”当作入口接通。

## 分层练习
L1 fake 模型下构造 Agent 并返回确定性结果；L2 接入真实聊天入口并装配提示/工具容器；L3 补角色、thread 隔离、流式/非流式；L4 验证空输入、重复请求、模型/构造失败。

## 交付与出口
交付 Agent input/output 契约、入口时序图、真实入口操作记录。你要能讲清一条用户消息如何进入 Agent 图、怎样得到响应，以及哪里开始保存状态。

## 跟着写代码：把模型包进 Agent

本章复用第 2 章的 `create_chat_model`，不在 Agent 中创建供应商客户端。示例文件可放在 `agents/lead_agent/agent.py`。

```python
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver


DEFAULT_SYSTEM_PROMPT = """
你是 WorkAgentHarness 的助手。
回答要清楚、准确；不知道时明确说明，不要编造事实。
""".strip()


def make_lead_agent(
    model: BaseChatModel,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
):
    """构造一个最小对话 Agent；模型由调用方注入，便于替换 fake。"""
    return create_agent(
        model=model,             # 使用第 2 章创建的模型实例
        tools=[],                 # 本篇先不加工具；第二篇学习工具接入
        middleware=[],            # 先保持执行路径短，后续再加入横切逻辑
        checkpointer=checkpointer,  # 第 3 章可传 None；第 4 章接入 SQLite saver
        system_prompt=system_prompt,
    )
```

逐句读 `create_agent` 的参数：模型与提示是本章必需依赖，tools 和 middleware 明确为空。不要传入 `tools=None` 后假设库会怎样处理，也不要用可变默认参数保存共享工具列表。

在临时 CLI 或交互式 Python 中调用：

```python
model = create_chat_model(load_chat_model_config("config.yaml"))
agent = make_lead_agent(model)

result = agent.invoke(
    {"messages": [("user", "请用三句话解释什么是 Agent。")]},
)
answer = result["messages"][-1].content  # 最后一条消息是 AI 的响应
print(answer)
```

这时没有 checkpointer，调用结束后图状态不会自动恢复。第 4 章会加 thread id 和持久化，因此这里不要提前把会话恢复逻辑塞进 Agent。

### 接入项目入口时的边界

入口层把外部请求转为 Agent 输入，核心 Agent 不接触 HTTP Request、终端 stdin 或具体 UI 类型。先用下面的薄函数表达这个边界；下一章会把它改为带 session/run 生命周期的应用服务。

```python
def answer_once(agent, user_text: str) -> str:
    """单轮用例：只接受纯文本，返回纯文本，不处理协议和存储。"""
    if not user_text.strip():
        raise ValueError("用户输入不能为空")  # 输入边界在调用模型前失败
    result = agent.invoke({"messages": [("user", user_text)]})
    return str(result["messages"][-1].content)
```

本章结束时，应能用 fake 模型替换真实 provider 而不修改 `make_lead_agent`，并能从用户入口追到 `answer_once` 和模型调用。
