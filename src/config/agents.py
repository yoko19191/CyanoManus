from typing import Literal

LLMType = Literal["basic", "reasoning", "vision", "coding"]

AGENT_LLM_MAP : dict[str, LLMType] = {
    "coordinator": "basic", # 使用标准模型, 执行多 Agent 的协调
    "planner": "reasoning", # 使用推理模型, 进行任务的编排
    "supervisor": "reasoning",  # 使用标准模型, 进行结果执行的监督和反馈
    "researcher": "basic", # 使用标准模型, 进行信息的搜集分析
    "retriever": "basic", # 使用标准模型, 进行 RAG 和 SQL 操作
    "coder": "coding", # 使用编程特化模型(e.g.deepseek-v3, claude-sonnet-3-7), 进行编程
    "reporter": "basic", # 使用标准模型, 递交最终的报告
    "operator": "vision" # 使用多模态模型，操作 GUI 和 浏览器
}





