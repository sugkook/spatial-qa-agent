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

## 面试讲解要点

### 1. 为什么用 LangGraph 而不是简单的 Chain？
- **状态管理**：4个节点共享 AgentState，每步结果可追溯
- **条件路由**：出错时跳过中间节点直接到 format_response
- **可扩展**：后续加 Multi-Agent（如一个Agent管查询、一个管可视化）只需加节点

### 2. 意图解析为什么用 LLM 而不是规则？
- 用户表达千变万化（"附近有啥吃的" / "这周围有餐厅吗" / "Find cafes near me"）
- LLM天然理解语义变体，规则写不完
- System Prompt 约束了输出为结构化 JSON，保证下游节点可解析

### 3. 空间工具有什么设计考量？
- **POI类型映射表**：中文"咖啡店" → OSM标签 {"amenity": "cafe"}，降低用户认知负担
- **默认参数**：未指定距离时给合理默认值（POI搜索500m、找最近2000m）
- **结果排序**：按距离升序，只返回TOP20，避免数据过载

### 4. 为什么做这个项目（你的差异化叙事）？
- 市面上Agent项目大多是「查天气+算数学」的玩具Demo
- 你把3年GIS专业积累转化为Agent的领域能力，形成**不可替代性**
- 面试官见过的候选人都会用LangChain调API，但会做空间分析的Agent凤毛麟角

### 5. 后续可扩展方向（展示产品思维）
- 接入高德/百度地图API替代Nominatim（国内地址更准）
- 加入RAG：用项目文档做知识库，用户问"这个区域的规划要求是什么"
- 多轮对话：记住上一轮的查询范围，用户说"再远一点"能自动扩半径
- PostGIS替代osmnx：百万级数据下的生产级方案
