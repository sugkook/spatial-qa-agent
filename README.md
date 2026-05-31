# 空间数据智能问答Agent

> 基于 LangGraph 的 GIS + AI Agent 项目 —— 面试展示用

## 一句话描述

**用户用自然语言问空间问题（"三里屯500米内有什么咖啡店"），Agent自动完成地理编码→空间查询→结果汇总→自然语言回答。**

## 架构

```
用户输入 "三里屯500米内的咖啡店"
    │
    ▼
┌──────────────────────┐
│ Node 1: 意图解析      │  LLM 分析 → intent=buffer_search
│ parse_intent         │  tool_args={address:"三里屯",radius:500,type:"咖啡店"}
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Node 2: 查询生成      │  校验工具名 + 参数
│ generate_query       │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Node 3: 查询执行      │  调用 osmnx API → geopandas 处理
│ execute_query        │  → 返回 [{name:"星巴克",distance:"120m"}, ...]
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Node 4: 结果格式化    │  LLM 将结构化结果 → 自然语言
│ format_response      │  "三里屯500米内有3家咖啡店：星巴克(120m)..."
└──────────────────────┘
```

## 技术栈

| 层级 | 技术 | 作用 |
|------|------|------|
| 工作流编排 | LangGraph (StateGraph) | 4节点流水线 + 条件路由 |
| LLM | GPT-4o / DeepSeek | 意图解析 + 结果格式化 |
| 空间计算 | osmnx + geopandas + shapely | OSM数据获取 + 空间分析 |
| 地理编码 | geopy (Nominatim) | 地址↔坐标转换 |
| API服务 | FastAPI + SSE | HTTP接口 + 流式响应 |
| 前端 | Streamlit + Folium | 聊天界面 + 地图可视化 |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置API Key（二选一）
export OPENAI_API_KEY="sk-xxx"
# 或改用DeepSeek（在agent.py中替换ChatOpenAI的model参数）

# 3. 启动后端
python server.py
# → http://localhost:8080

# 4. 启动前端（新终端）
streamlit run frontend.py
# → http://localhost:8501
```

## 项目文件

```
spatial-agent/
├── agent.py           # LangGraph工作流（核心）
├── spatial_tools.py   # 空间工具函数（6个）
├── server.py          # FastAPI接口
├── frontend.py        # Streamlit聊天界面
├── requirements.txt   # 依赖
└── README.md
```

