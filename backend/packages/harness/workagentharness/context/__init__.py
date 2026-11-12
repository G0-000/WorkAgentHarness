"""上下文治理工具（第四篇）。

对应 EvoFlow ``evoflow/context/`` 目录，只实现第 14 章需要的三块：
    token_budget.py      ← context/model_request_token_estimate.py
    tool_history_merge.py← context/tool_history_merge.py
    compaction_state.py  ← 折叠计数与 pinned 标记（原版散落在 middleware 内）
"""

from __future__ import annotations

__all__: list[str] = []
