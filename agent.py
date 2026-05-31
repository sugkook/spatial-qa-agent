"""
空间智能问答Agent — LangGraph 工作流

核心流程（4个节点 + 条件路由）：
    parse_intent → generate_query → execute_query → format_response → END

依赖：pip install langgraph langchain langchain-openai
"""

import json
import os
import operator
from typing import Annotated, TypedDict, Literal

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from spatial_tools import (
    geocode,
    reverse_geocode,
    buffer_search,
    nearest_poi,
    calculate_route_info,
)

# 从环境变量读取 API Key（支持 OpenAI / DeepSeek 等兼容接口）
# 默认使用 DeepSeek，如需切换请修改环境变量或下方的 model/base_url
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-placeholder")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")

llm = ChatOpenAI(
    model=LLM_MODEL,
    base_url=LLM_BASE_URL,
    api_key=OPENAI_API_KEY,
    temperature=0,
)

TOOL_REGISTRY = {
    "geocode": geocode,
    "reverse_geocode": reverse_geocode,
    "buffer_search": buffer_search,
    "nearest_poi": nearest_poi,
    "calculate_route_info": calculate_route_info,
}


class AgentState(TypedDict):
    """LangGraph 共享状态"""
    user_input: str
    intent: str
    tool_name: str
    tool_args: dict
    tool_result: dict
    final_response: str
    error: str


# ─── Node 1: 意图解析 ───────────────────────────────────────────

INTENT_PROMPT = """你是一个空间查询意图解析器。分析用户输入，判断属于哪种空间查询类型。

类型定义：
- geocode: 地址转经纬度。例："天安门在哪"
- reverse_geocode: 经纬度转地址。例："39.9,116.4是什么地方"
- buffer_search: 在某地点周围找POI。例："三里屯500米内的咖啡店" "国贸附近的餐厅"
- nearest_poi: 找最近的某类POI。例："离我最近的医院" "最近的公园"
- calculate_route_info: 计算两点距离。例："从天安门到故宫多远"

返回JSON格式：
{
    "intent": "buffer_search",
    "tool_name": "buffer_search",
    "tool_args": {"address": "三里屯", "radius_m": 500, "poi_type": "咖啡店"},
    "reasoning": "用户想在三里屯周围500米找咖啡店"
}

注意：
1. 如果没有明确距离，用默认值：POI搜索默认500m，找最近默认2000m
2. poi_type用中文名称（如"咖啡店"而非"cafe"），spatial_tools会自动映射
3. 只返回JSON，不要其他文字"""


def parse_intent(state: AgentState) -> AgentState:
    """Node 1: LLM分析用户意图 → 提取工具名+参数"""
    response = llm.invoke([
        SystemMessage(content=INTENT_PROMPT),
        HumanMessage(content=state["user_input"]),
    ])
    try:
        parsed = json.loads(response.content)
        state["intent"] = parsed.get("intent", "unknown")
        state["tool_name"] = parsed.get("tool_name", "")
        state["tool_args"] = parsed.get("tool_args", {})
    except json.JSONDecodeError:
        state["error"] = f"意图解析失败: {response.content}"
        state["intent"] = "error"
    return state


# ─── Node 2: 查询生成（此处已整合在parse_intent中，本节点做校验+补充） ──

def generate_query(state: AgentState) -> AgentState:
    """Node 2: 校验工具存在性，必要时补充参数"""
    if state["intent"] == "error":
        return state

    tool_name = state["tool_name"]
    if tool_name not in TOOL_REGISTRY:
        state["error"] = f"未知工具: {tool_name}"
        state["intent"] = "error"
    return state


# ─── Node 3: 查询执行 ───────────────────────────────────────────

def execute_query(state: AgentState) -> AgentState:
    """Node 3: 调用空间工具，执行真实空间计算"""
    if state["intent"] == "error":
        return state

    tool_fn = TOOL_REGISTRY[state["tool_name"]]
    try:
        result = tool_fn(**state["tool_args"])
        state["tool_result"] = result
    except Exception as e:
        state["error"] = f"空间查询执行失败: {str(e)}"
        state["intent"] = "error"
    return state


# ─── Node 4: 结果格式化 ─────────────────────────────────────────

FORMAT_PROMPT = """你是一个空间数据助手。将以下空间查询结果转化为用户友好的自然语言回答。

要求：
1. 列出关键结果（POI名称、距离、类型）
2. 距离用"米"或"公里"表示
3. 如果结果很多，只展示TOP5，并说明还有更多
4. 语气自然，像真人对话
5. 200字以内，简洁清晰"""


def format_response(state: AgentState) -> AgentState:
    """Node 4: LLM将结构化结果转为自然语言"""
    if state["intent"] == "error":
        state["final_response"] = f"抱歉，查询出错了：{state['error']}"
        return state

    result_str = json.dumps(state["tool_result"], ensure_ascii=False, indent=2)
    response = llm.invoke([
        SystemMessage(content=FORMAT_PROMPT),
        HumanMessage(content=f"用户问题：{state['user_input']}\n查询结果：{result_str}"),
    ])
    state["final_response"] = response.content
    return state


# ─── 路由函数 ───────────────────────────────────────────────────

def route_after_parse(state: AgentState) -> Literal["generate_query", "format_response"]:
    return "format_response" if state["intent"] == "error" else "generate_query"


def route_after_execute(state: AgentState) -> Literal["format_response", END]:
    return "format_response"


# ─── 构建 Graph ─────────────────────────────────────────────────

def build_agent():
    """构建并编译 LangGraph 工作流"""
    workflow = StateGraph(AgentState)

    workflow.add_node("parse_intent", parse_intent)
    workflow.add_node("generate_query", generate_query)
    workflow.add_node("execute_query", execute_query)
    workflow.add_node("format_response", format_response)

    workflow.set_entry_point("parse_intent")
    workflow.add_conditional_edges("parse_intent", route_after_parse, {
        "generate_query": "generate_query",
        "format_response": "format_response",
    })
    workflow.add_edge("generate_query", "execute_query")
    workflow.add_edge("execute_query", "format_response")
    workflow.add_edge("format_response", END)

    return workflow.compile()


agent = build_agent()


def ask(question: str) -> str:
    """便捷调用函数"""
    result = agent.invoke({"user_input": question, "error": ""})
    return result["final_response"]


if __name__ == "__main__":
    while True:
        q = input("\n🗺️  请输入空间查询 (exit 退出): ").strip()
        if q.lower() == "exit":
            break
        print(f"\n🤖 {ask(q)}")
