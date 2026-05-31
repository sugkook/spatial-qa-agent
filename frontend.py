"""前端聊天页面 —— 与 Agent 对话的可视化界面

依赖：pip install folium streamlit
启动：streamlit run frontend.py
"""

import streamlit as st
import requests
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
import json

st.set_page_config(page_title="空间智能问答Agent", page_icon="🗺️", layout="wide")

st.title("🗺️ 空间数据智能问答 Agent")
st.caption("用自然语言查询地理空间数据 — 基于 LangGraph + OSM + DeepSeek")

st.markdown("""
**试试这些问法：**
- 三里屯500米内有什么咖啡店？
- 天安门的经纬度是多少？
- 离故宫最近的医院有哪些？
- 从天安门到鸟巢有多远？
- 中关村周围1公里内有哪些餐厅？
""")

if "messages" not in st.session_state:
    st.session_state.messages = []

question = st.chat_input("输入你的空间查询...")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("map_html"):
            st.components.v1.html(msg["map_html"], height=400)

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("正在查询..."):
            try:
                resp = requests.post(
                    "http://localhost:8080/ask",
                    json={"question": question},
                    timeout=60,
                )
                data = resp.json()

                st.markdown(data.get("answer", "抱歉，出了点问题"))

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("意图识别", data.get("intent", "-"))
                with col2:
                    st.metric("调用工具", data.get("tool_name", "-"))

                tool_result = data.get("tool_result", {})
                if tool_result.get("pois"):
                    pois = tool_result["pois"][:10]
                    st.markdown(f"**找到 {tool_result['count']} 个结果**")
                    st.dataframe(
                        [{"名称": p["name"], "类型": p["type"], "距离": f"{p['distance_m']}m"}
                         for p in pois],
                        use_container_width=True,
                    )

                    center = tool_result.get("center", {})
                    if center:
                        m = folium.Map(
                            location=[center.get("lat", 39.9), center.get("lon", 116.4)],
                            zoom_start=14,
                        )
                        marker_cluster = MarkerCluster().add_to(m)
                        for p in pois:
                            folium.Marker(
                                [p["lat"], p["lon"]],
                                popup=f"{p['name']} ({p['distance_m']}m)",
                                tooltip=p["name"],
                            ).add_to(marker_cluster)
                        folium_static(m, width=700, height=400)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": data.get("answer", ""),
                })

            except requests.ConnectionError:
                st.error("❌ 无法连接到后端服务，请先启动 `python server.py`")
            except Exception as e:
                st.error(f"❌ 查询出错：{e}")
