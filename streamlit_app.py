import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import branca.colormap as cm
import os
import warnings

warnings.filterwarnings("ignore")

# 设置页面
st.set_page_config(page_title="大连近岸海域抗生素及水环境激素风险管控平台", layout="wide")

# 自定义CSS样式 - 增大全局字体并设置样式
st.markdown("""
<style>
    /* 增大全局字体大小 */
    html, body, [class*="css"] {
        font-size: 20px !important;
    }

    /* 增大标题字体 */
    h1 {
        font-size: 58px !important;
    }
    h2 {
        font-size: 30px !important;
    }
    h3 {
        font-size: 30px !important;
    }

    /* 按钮样式优化 */
    .stButton > button {
        font-size: 20px !important;
        padding: 10px 20px !important;
    }

    /* 输入框样式 */
    .stTextInput > div > div > input {
        font-size: 20px !important;
        padding: 10px !important;
    }

    /* 调整radio按钮字体 */
    [data-testid="stRadio"] label {
        font-size: 24px !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("大连近岸海域抗生素及水环境激素风险管控平台")

# 1. 初始化session_state（新增参数范围存储）
if 'map_center' not in st.session_state:
    st.session_state.map_center = [39.618, 122.228]
    st.session_state.map_zoom = 8
    st.session_state.last_params = None
    st.session_state.pending_reset = False
    st.session_state.last_map_key = 0
    st.session_state.cas_data_loaded = False
    st.session_state.cas_data = None
    st.session_state.param_ranges = None  # 存储各参数的min和max


# 检查文件是否存在的辅助函数
def file_exists(file_path):
    return os.path.exists(file_path)


# 2. 侧边栏（包含设置和下载功能）
with st.sidebar:
    # 空标题单选按钮
    selected_tab = st.radio("功能设置", ["浓度地图展示", "CAS号查询"], label_visibility="hidden")

    if selected_tab == "浓度地图展示":
        # 先加载数据以获取参数范围（复用已有的加载函数）
        @st.cache_data
        def load_concentration_data():
            try:
                df = pd.read_excel("浓度点位数据.xlsx")
                required_cols = ['站位', '采样时间', '经度', '纬度', '水温℃', '盐度', 'pH', '溶解氧mg/L']
                missing_cols = [col for col in required_cols if col not in df.columns]
                if missing_cols:
                    st.error(f"Excel文件缺少必要列：{', '.join(missing_cols)}")
                    return None
                return df
            except FileNotFoundError:
                st.error("未找到'浓度点位数据.xlsx'文件，请确保文件在正确路径下")
                return None
            except Exception as e:
                st.error(f"读取数据出错：{str(e)}")
                return None


        df = load_concentration_data()

        # 计算各参数的min和max并存储到session_state
        if df is not None:
            param_cols = ["水温℃", "盐度", "pH", "溶解氧mg/L"]
            st.session_state.param_ranges = {
                col: {
                    "min": float(df[col].min()),
                    "max": float(df[col].max())
                } for col in param_cols
            }

        # 显示参数选择器（依赖数据加载结果）
        if st.session_state.param_ranges is not None:
            selected_param = st.selectbox("显示参数", ["水温℃", "盐度", "pH", "溶解氧mg/L"])

            # 从session_state获取当前参数的min和max（动态更新）
            current_range = st.session_state.param_ranges[selected_param]
            min_value = current_range["min"]  # 固定为最小值，确保所有数据都显示
            # min_value = st.slider(
            #     f"{selected_param}",
            #     min_value=current_range["min"],  # 数据中的最小值
            #     max_value=current_range["max"],  # 数据中的最大值
            #     value=current_range["min"]  # 默认值设为最小值
            # )
        else:
            # 数据加载失败时禁用滑块
            selected_param = st.selectbox("显示参数", ["水温℃", "盐度", "pH", "溶解氧mg/L"], disabled=True)
            min_value = 0.0  # 占位值，数据加载失败时无实际意义

        map_type = st.radio("地图类型", ["标准地图", "卫星影像"], horizontal=True)

        if st.button("重置地图视图", use_container_width=True):
            st.session_state.pending_reset = True
            st.rerun()

    # 下载区域（保持不变）
    conc_file = "浓度点位数据.xlsx"
    if file_exists(conc_file):
        with open(conc_file, "rb") as f:
            st.download_button(
                label="下载浓度点位数据",
                data=f,
                file_name=conc_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    else:
        st.download_button(
            label="下载浓度点位数据",
            data=b"",
            file_name=conc_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            disabled=True
        )
        st.warning(f"未找到{conc_file}文件")

    toxic_file = "./毒性数据.xlsx"
    if file_exists(toxic_file):
        with open(toxic_file, "rb") as f:
            st.download_button(
                label="下载毒性数据",
                data=f,
                file_name="毒性数据.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    else:
        st.download_button(
            label="下载毒性数据",
            data=b"",
            file_name="毒性数据.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            disabled=True
        )
        st.warning(f"未找到{toxic_file}文件")

# 3. 处理重置请求（保持不变）
if st.session_state.pending_reset:
    st.session_state.map_center = [39.618, 122.228]
    st.session_state.map_zoom = 8
    st.session_state.pending_reset = False
    st.session_state.last_map_key += 1

# 4. 浓度地图展示功能（保持不变，复用之前的逻辑）
if selected_tab == "浓度地图展示":
    st.subheader("📍 浓度地图展示")

    # 复用数据加载函数（已在侧边栏加载过，这里直接获取）
    df = load_concentration_data()

    if df is not None:
        def create_map():
            if map_type == "标准地图":
                tiles_url = "https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}"
            else:
                tiles_url = "https://webst01.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}"

            m = folium.Map(
                location=st.session_state.map_center,
                zoom_start=st.session_state.map_zoom,
                tiles=tiles_url,
                attr="高德地图",
                control_scale=True
            )
            return m


        def create_map_with_markers():
            m = create_map()
            param_values = df[selected_param]
            max_val = max(param_values.max(), 1)
            colormap = cm.LinearColormap(
                colors=['blue', 'green', 'yellow', 'orange', 'red'],
                vmin=param_values.min(),
                vmax=max_val
            )
            colormap.caption = selected_param
            m.add_child(colormap)

            for _, row in df.iterrows():
                # if row[selected_param] >= min_value:

                popup = f"""
                <style>
                    .popup-title {{font-size: 13px; font-weight: bold; margin: 2px 0;}}
                    .popup-text {{font-size: 11px; margin: 1px 0;}}
                </style>
                <div class="popup-title">站位：{row['站位']}</div>
                <div class="popup-text">采样时间：{row['采样时间']}</div>
                <div class="popup-text">经纬度：{row['纬度']:.4f}, {row['经度']:.4f}</div>
                <div class="popup-text">{selected_param}：{row[selected_param]}</div>
                <div class="popup-text">盐度：{row['盐度']}</div>
                <div class="popup-text">pH：{row['pH']}</div>
                <div class="popup-text">溶解氧mg/L：{row['溶解氧mg/L']}</div>
                """
                color = colormap(row[selected_param])
                folium.CircleMarker(
                    location=[row['纬度'], row['经度']],
                    radius=8,
                    popup=folium.Popup(popup, max_width=200),
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.7
                ).add_to(m)

            return m

        current_params = (selected_param, min_value, map_type)
        st.session_state.last_params = current_params

        map_key = f"map_{st.session_state.last_map_key}"
        map_data = st_folium(
            create_map_with_markers(),
            width=1100,
            height=550,
            key=map_key,
            returned_objects=["center", "zoom"]
        )

        if map_data.get("center") and map_data.get("zoom"):
            st.session_state.map_center = [map_data["center"]["lat"], map_data["center"]["lng"]]
            st.session_state.map_zoom = map_data["zoom"]

        st.caption(f"地图状态已更新 | 中心点: {st.session_state.map_center} | 缩放: {st.session_state.map_zoom}")


# 5. CAS号查询功能（保持不变）
else:  # selected_tab == "CAS号查询"
    st.subheader("🔍 CAS号查询")

    if not st.session_state.cas_data_loaded:
        try:
            with st.spinner("正在加载毒性数据..."):
                temp_data = pd.read_excel('./毒性数据.xlsx', sheet_name='MM-GCN预测毒性数据集')
                temp_data.columns = temp_data.iloc[0]
                temp_data = temp_data.drop(temp_data.index[0])
                temp_data = temp_data.reset_index(drop=True)
                if 'CAS' in temp_data.columns:
                    temp_data['CAS'] = temp_data['CAS'].astype(str)
                st.session_state.cas_data = temp_data
                st.session_state.cas_data_loaded = True
        except FileNotFoundError:
            st.error("未找到'毒性数据.xlsx'文件，请确保文件在正确路径下")
        except Exception as e:
            st.error(f"读取毒性数据出错：{str(e)}")

    if st.session_state.cas_data_loaded and st.session_state.cas_data is not None:
        cas_numbers = st.session_state.cas_data['CAS'].dropna().unique().tolist()
        cas_numbers = [str(cas) for cas in cas_numbers]

        cas_input = st.text_input("CAS号输入框", placeholder="例如：1912-24-9", label_visibility='hidden')

        col1, col2 = st.columns([1, 4])
        with col1:
            search_btn = st.button("查询", use_container_width=True)

        if search_btn and cas_input:
            cas_input_str = str(cas_input)
            result = st.session_state.cas_data[st.session_state.cas_data['CAS'] == cas_input_str]

            if not result.empty:
                st.markdown(
                    f"""
                    <div style="background-color:#f0f8ff; padding:10px; border-radius:4px; margin-bottom:12px;">
                        ✅ 找到CAS号为 {cas_input_str} 的记录
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                result_row = result.iloc[0]
                test_fields = ['AD 检验', 'KS 检验', 'JB 检验']
                other_fields = [field for field in result.columns if field not in test_fields]

                # ---------- 关键修改：用网格布局实现对齐 ----------
                # 每行分2列：左列（表头）+ 右列（数值）
                for field_name in other_fields:
                    field_value = result_row[field_name]
                    display_value = str(field_value) if pd.notna(field_value) else "无数据"

                    # 定义左右列（左列固定宽度，右列自适应）
                    col_left, col_right = st.columns([2, 3])
                    with col_left:
                        st.markdown(
                            f"""
                            <div style="background-color:#f0f8ff;padding:10px; border-radius:4px; margin-bottom:8px; text-align:right;">
                                <strong>{field_name}：</strong>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    with col_right:
                        st.markdown(
                            f"""
                            <div style="padding:10px; border-radius:4px; margin-bottom:8px; text-align:left;">
                                <span>{display_value}</span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                # 测试结果部分保持原逻辑
                test_cols = st.columns(3)
                for i, field_name in enumerate(test_fields):
                    field_value = result_row[field_name]
                    display_value = str(field_value) if pd.notna(field_value) else "无数据"

                    if str(field_value).lower() == "true":
                        color = "#28a745"
                        icon = "✅"
                    else:
                        color = "#dc3545"
                        icon = "❌"

                    with test_cols[i]:
                        st.markdown(
                            f"""
                            <div style="padding:10px; border-radius:4px; margin-bottom:8px; text-align:center;">
                                <strong>{field_name}</strong>
                                <div style="color:{color}; font-size:24px; margin-top:5px;">
                                    {icon} {display_value}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.warning(f"未找到CAS号为 {cas_input_str} 的记录")
