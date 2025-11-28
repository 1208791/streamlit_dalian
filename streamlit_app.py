import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import branca.colormap as cm
import os
import warnings
import numpy as np
import base64
import json

st.set_option("client.toolbarMode", "viewer")


# --- 定义一个函数来读取图片并转换为base64 ---
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()


warnings.filterwarnings("ignore")

# -------------------------
# 页面与样式设置
# -------------------------
st.set_page_config(page_title="大连近岸海域抗生素及环境激素风险管控平台", layout="wide", initial_sidebar_state="collapsed")


def set_global_font_size(size="16px"):
    st.markdown(f"""
    <style>
    html, body, [class*="css"] {{
        font-size: {size} !important;
    }}
    </style>
    """, unsafe_allow_html=True)


set_global_font_size("30px")


def set_background(png_file):
    bin_str = get_base64_of_bin_file(png_file)
    page_bg_img = f'''
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{bin_str}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    </style>
    '''
    st.markdown(page_bg_img, unsafe_allow_html=True)


# set_background('homepage_image.png')

# 隐藏 Streamlit 默认侧边栏与顶部菜单
st.markdown("""
    <style>
        /* 隐藏侧边栏 */
        [data-testid="stSidebar"] { display: none; }
        [data-testid="collapsedControl"] { display: none; }

        div[data-testid="stToolbar"] {
            display: none !important;
        }
        div[data-testid="stDecoration"] {
            display: none !important;
        }
        div[data-testid="stStatusWidget"] {
            visibility: hidden !important;
        }

        /* 卡片与按钮样式 */
        .func-card {
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 16px;
            border: 1px solid #E6EEF8;
            background: linear-gradient(180deg,#ffffff,#f6fbff);
            box-shadow: 0 6px 18px rgba(38,78,119,0.06);
        }
        .func-title { 
            font-size: 20px; 
            font-weight:500; 
            margin-bottom:6px; 
            color:#003366; 
        }
        .func-desc { 
            font-size:14px; 
            color:#333; 
            margin-bottom:8px; 
        }
        .func-btn {
            background-color:#0b5bd7;
            color:white;
            padding:8px 14px;
            border-radius:8px;
            border: none;
            font-weight:600;
        }
        .func-btn:hover { 
            opacity: 0.9; 
            cursor: pointer; 
        }

        /* 改变输入框的字体大小和高度 */
        div.stTextInput>div>div>input {
            font-size: 30px;   /* 字体大小 */
            line-height: 50px;      /* 输入框高度 */
        }

        /* --- 1. 全局Streamlit按钮样式 (背景、尺寸等) --- */
        div.stButton > button:first-child {
            background: linear-gradient(135deg, #0723f2, #1375f9) !important;
            color: white !important;
            padding: 0.5rem 1.25rem !important;
            border-radius: 0.25rem !important;
            border: none !important;
            cursor: pointer !important;
            width: 400px !important;
            height: 50px !important;
            transition: all 0.3s ease !important;
        }

        /* --- 3. 按钮悬停效果 --- */
        div.stButton > button:first-child:hover {
            opacity: 0.9 !important;
            background: linear-gradient(135deg, #0723f2, #1375f9) !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
        }

        /* 自定义数据面板样式 */
        .data-panel {
            border: 3px solid #0b5bd7;
            border-radius: 15px;
            padding: 25px;
            background-color: #f0f8ff;
            height: 100%; /* 让面板占满列的高度 */
            overflow-y: auto; /* 如果内容太多，显示滚动条 */
            box-shadow: 0 6px 18px rgba(11, 91, 215, 0.1);
        }
        .data-panel h4 {
            color: #0b5bd7;
            border-bottom: 2px solid #0b5bd7;
            padding-bottom: 10px;
            margin-top: 0;
        }
    </style>
""", unsafe_allow_html=True)

# -------------------------
# session_state 初始化
# -------------------------
if 'page' not in st.session_state:
    st.session_state.page = "home"  # 'home', 'map', 'cas'

# 新增：用于存储点击的点位数据
if 'clicked_point_data' not in st.session_state:
    st.session_state.clicked_point_data = None

# 地图与数据状态
if 'map_center' not in st.session_state:
    st.session_state.map_center = [39.618, 122.228]
    st.session_state.map_zoom = 8
    st.session_state.last_map_key = 0
    st.session_state.all_param_cols = []
    st.session_state.param_ranges = {}
    st.session_state.cas_data_loaded = False
    st.session_state.cas_data = None
    st.session_state.excel_columns = []


# -------------------------
# 共享辅助函数
# -------------------------
def file_exists(file_path):
    return os.path.exists(file_path)


def load_concentration_data(filepath="浓度点位数据v1.xlsx"):
    try:
        df = pd.read_excel(filepath)
        df.columns = df.columns.astype(str).str.strip().str.replace('\n', '').str.lower()
        st.session_state.excel_columns = df.columns.tolist()
        base_cols_clean = ['分类', '序号', '站位', '采样时间', '经度', '纬度']
        missing_base_cols = [col for col in base_cols_clean if col not in df.columns]
        if missing_base_cols:
            st.error(f"Excel 缺少基础列（小写匹配后）：{', '.join(missing_base_cols)}")
            return pd.DataFrame()
        df = df.dropna(subset=['经度', '纬度']).reset_index(drop=True)
        exclude_cols = ['水深', '水温℃', '盐度', 'ph', '溶解氧mg/l']
        param_cols = [col for col in df.columns if col not in base_cols_clean and col not in exclude_cols]
        param_cols_original = [col.capitalize() if col not in ['经度', '纬度'] else col for col in param_cols]
        st.session_state.all_param_cols = param_cols_original

        param_ranges = {}
        for col in param_cols_original:
            lower = col.lower()
            if lower not in df.columns:
                param_ranges[col] = {"min": None, "max": None}
                continue
            numeric_series = pd.to_numeric(df[lower], errors='coerce').dropna()
            if not numeric_series.empty:
                param_ranges[col] = {"min": float(numeric_series.min()), "max": float(numeric_series.max())}
            else:
                param_ranges[col] = {"min": None, "max": None}
        st.session_state.param_ranges = param_ranges
        return df
    except FileNotFoundError:
        st.error(f"未找到文件：{filepath}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"读取浓度数据出错：{e}")
        return pd.DataFrame()


def load_cas_data(filepath="./毒性数据.xlsx", sheet="MM-GCN预测毒性数据集"):
    try:
        temp_data = pd.read_excel(filepath, sheet_name=sheet)
        temp_data.columns = temp_data.iloc[0]
        temp_data = temp_data.drop(temp_data.index[0]).reset_index(drop=True)
        if 'CAS' in temp_data.columns:
            temp_data['CAS'] = temp_data['CAS'].astype(str)
        st.session_state.cas_data = temp_data
        st.session_state.cas_data_loaded = True
        return temp_data
    except FileNotFoundError:
        st.error(f"未找到文件：{filepath}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"读取毒性数据出错：{e}")
        return pd.DataFrame()


# -------------------------
# 路由函数
# -------------------------
def goto(page_name):
    st.session_state.page = page_name
    # 切换页面时清空点击数据
    st.session_state.clicked_point_data = None
    try:
        st.rerun()
    except AttributeError:
        try:
            st.experimental_rerun()
        except Exception as e:
            st.warning(f"页面跳转需要Streamlit 1.18.0+版本。错误：{e}")


# -------------------------
# 首页
# -------------------------
def page_home():
    st.markdown(
        "<h1 style='text-align:center;margin-top:-100px;font-size: 65px;'>大连近岸海域抗生素及环境激素风险管控平台</h1>",
        unsafe_allow_html=True)

    # 页面布局：左图 (宽) , 右功能卡 (窄)
    col1, col2 = st.columns([2, 1], gap="large")

    with col1:
        img_path = "homepage_image.png"
        st.image(img_path, width='stretch')

    with col2:
        with st.container():
            st.markdown("<div class='func-title' style='font-size: 60px;'>浓度数据</div>",
                        unsafe_allow_html=True)

            if st.button("进入浓度地图", key="btn_map", type="primary"):
                goto("map")

        with st.container():

            st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

            # 功能卡2：CAS查询
            st.markdown("<div class='func-title' style='font-size: 60px;'>毒性数据</div>",
                        unsafe_allow_html=True)

            if st.button("进入CAS查询", key="btn_cas", type="primary"):
                goto("cas")

    st.markdown("---")
    # 平台说明
    st.markdown("""
    <div style="color:#444;font-size:40px;">
        本平台由 <b>大连理工大学环境学院</b> 开发
    </div>
    """, unsafe_allow_html=True)


# -------------------------
# 浓度地图页面 (修复版本)
# -------------------------
def page_map():
    st.header("大连近岸海域抗生素及环境激素浓度地图")

    # 页面布局：左侧地图，右侧数据面板
    df = load_concentration_data("浓度点位数据v1.xlsx")
    if df.empty:
        st.warning("未加载到有效浓度数据，返回首页查看帮助或检查文件。")
        return

    if st.session_state.all_param_cols:
        selected_param = st.selectbox("", st.session_state.all_param_cols)
    else:
        st.warning("未识别到参数列。请检查 Excel 列名。")
        return

    def create_map():
        tiles_url = "https://webst01.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}"
        m = folium.Map(
            location=st.session_state.map_center,
            zoom_start=st.session_state.map_zoom,
            tiles=tiles_url,
            attr="地图",
            control_scale=True
        )
        return m

    def create_map_with_markers(selected_param):
        m = create_map()
        param_col_clean = selected_param.lower()
        param_valid = pd.to_numeric(df[param_col_clean], errors='coerce').dropna()
        if param_valid.empty:
            st.warning(f"当前选择的参数【{selected_param}】无有效数值数据，标记将显示灰色。")
            colormap = None
        else:
            max_val = max(param_valid.max(), 1e-9)
            colormap = cm.LinearColormap(['blue', 'green', 'yellow', 'orange', 'red'], vmin=param_valid.min(),
                                         vmax=max_val)
            colormap.caption = f"{selected_param} 浓度"
            m.add_child(colormap)

        # 创建一个 FeatureGroup 来存储所有标记
        feature_group = folium.FeatureGroup(name="浓度点位")

        for idx, row in df.iterrows():
            lat, lng = row['纬度'], row['经度']

            # 准备基础水文数据（必显示）
            base_data = {
                '站位': row.get('站位', '未知'),
                # '分类': row.get('分类', '未知'),
                '采样时间': row.get('采样时间', '未知'),
                '纬度': round(lat, 4),
                '经度': round(lng, 4),
            }
            # 只获取当前选中参数的浓度
            selected_val = row.get(param_col_clean, np.nan)
            base_data[selected_param] = f"{float(selected_val):.4f}" if pd.notna(selected_val) else "无数据"

            # 创建弹窗内容：仅显示基础水文信息 + 当前选中参数浓度
            popup_html = f"""
                <div style="font-size:14px; width:250px;">
                <strong>站位：</strong>{base_data['站位']}<br>
                <strong>采样时间：</strong>{base_data['采样时间']}<br>
                <strong>经纬度：</strong>{base_data['纬度']}, {base_data['经度']}<hr>
                <strong style="color:#0b5bd7;">{selected_param}：</strong>{base_data[selected_param]}<br>
                </div>
            """

            # 决定标记点颜色
            color = "#808080"
            if not pd.isna(row[param_col_clean]) and colormap:
                try:
                    color = colormap(float(row[param_col_clean]))
                except:
                    pass

            # 创建标记点
            marker = folium.CircleMarker(
                location=[lat, lng],
                radius=8,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                popup=folium.Popup(popup_html, max_width=300)
            )

            marker.add_to(feature_group)

        feature_group.add_to(m)

        # 添加点击事件处理的JavaScript
        click_js = """
        <script>
        // 监听地图点击事件
        document.addEventListener('DOMContentLoaded', function() {
            const map = document.querySelector('.folium-map');
            if (map) {
                map.addEventListener('click', function(e) {
                    // 检查是否点击了标记
                    if (e.target.closest('.leaflet-marker-icon') || e.target.closest('.leaflet-popup-content')) {
                        // 标记点击已经在popup中处理
                        return;
                    }
                    // 点击地图空白处，清空选中数据
                    window.parent.postMessage({
                        type: 'streamlit:setSessionState',
                        data: { clicked_point_data: null }
                    }, '*');
                });
            }
        });
        </script>
        """
        m.get_root().html.add_child(folium.Element(click_js))

        return m

    # 在左侧列中显示地图
    map_key = f"map_{st.session_state.last_map_key}_{selected_param}"
    map_data = st_folium(create_map_with_markers(selected_param), width=1200, height=800, key=map_key,
                         returned_objects=["center", "zoom", "last_object_clicked"])

    if map_data and map_data.get("center") and map_data.get("zoom"):
        st.session_state.map_center = [map_data["center"]["lat"], map_data["center"]["lng"]]
        st.session_state.map_zoom = map_data["zoom"]

    # 处理通过last_object_clicked传递的数据：仅存储基础信息+当前选中参数
    if map_data and map_data.get("last_object_clicked"):
        clicked_lat = map_data["last_object_clicked"]["lat"]
        clicked_lng = map_data["last_object_clicked"]["lng"]

        # 查找对应的数据点
        tolerance = 0.01  # 容差范围
        matched_rows = df[
            (abs(df['纬度'] - clicked_lat) < tolerance) &
            (abs(df['经度'] - clicked_lng) < tolerance)
            ]

        if not matched_rows.empty:
            row = matched_rows.iloc[0]
            # 仅存储基础水文信息和当前选中参数
            point_data = {
                '站位': row.get('站位', '未知'),
                # '分类': row.get('分类', '未知'),
                '采样时间': row.get('采样时间', '未知'),
                '纬度': round(row['纬度'], 4),
                '经度': round(row['经度'], 4),
                selected_param: f"{float(row.get(selected_param.lower(), np.nan)):.4f}"
                                if pd.notna(row.get(selected_param.lower(), np.nan)) else "无数据"
            }
            st.session_state.clicked_point_data = point_data

            # 显示点击后的详情面板（仅基础信息+选中参数）
            # st.markdown("---")
            # st.markdown(f"<h3>点位详情 - {point_data['站位']}</h3>", unsafe_allow_html=True)
            # with st.container(class_="data-panel"):
            #     col1, col2 = st.columns(2)
            #     with col1:
            #         # st.markdown(f"<strong>分类：</strong>{point_data['分类']}", unsafe_allow_html=True)
            #         st.markdown(f"<strong>采样时间：</strong>{point_data['采样时间']}", unsafe_allow_html=True)
            #         st.markdown(f"<strong>纬度：</strong>{point_data['纬度']}", unsafe_allow_html=True)
            #         st.markdown(f"<strong>经度：</strong>{point_data['经度']}", unsafe_allow_html=True)
            #     with col2:
            #         st.markdown(f"<strong style='color:#0b5bd7; font-size:28px;'>{selected_param}：</strong>{point_data[selected_param]}",
            #                    unsafe_allow_html=True)

    # 返回首页按钮和下载按钮
    st.markdown("---")
    conc_file = "浓度点位数据v1.xlsx"
    if file_exists(conc_file):
        with open(conc_file, "rb") as f:
            st.download_button("下载浓度点位数据", data=f, file_name=conc_file)
    back_col, _ = st.columns([1, 9])
    with back_col:
        if st.button("← 返回首页"):
            goto("home")

# -------------------------
# CAS 查询页面
# -------------------------
def page_cas():
    st.markdown(
        "<div class='func-title' style='font-size: 60px; font-weight: 700;'>CAS 号查询</div>",
        unsafe_allow_html=True
    )

    if not st.session_state.cas_data_loaded:
        temp = load_cas_data("./毒性数据.xlsx")
        if temp.empty:
            st.warning("毒性数据未加载，请检查文件。")
            return

    if st.session_state.cas_data is None or st.session_state.cas_data.empty:
        st.warning("毒性数据为空，请检查源文件。")
        return

    cas_input = st.text_input("", placeholder="例如：1912-24-9")
    if st.button("查询"):
        if not cas_input:
            st.warning("请输入 CAS 号")
        else:
            cas_input_str = str(cas_input).strip()
            result = st.session_state.cas_data[st.session_state.cas_data['CAS'] == cas_input_str]
            if not result.empty:
                st.markdown(
                    f"""
                    <div style="background-color:#f0f8ff; padding:10px; border-radius:4px; margin-bottom:12px;font-size:30px">
                        ✅ 找到CAS号为 {cas_input_str} 的记录
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                result_row = result.iloc[0]
                test_fields = ['AD 检验', 'KS 检验', 'JB 检验']
                other_fields = [field for field in result.columns if field not in test_fields]

                for field_name in other_fields:
                    field_value = result_row[field_name]
                    display_value = str(field_value) if pd.notna(field_value) else "无数据"
                    col_left, col_right = st.columns([2, 3])
                    with col_left:
                        st.markdown(
                            f"<div style='background-color:#f0f8ff;padding:10px; border-radius:4px; margin-bottom:8px; text-align:right;font-size:25px;'><strong>{field_name}：</strong></div>",
                            unsafe_allow_html=True)
                    with col_right:
                        st.markdown(
                            f"<div style='padding:10px; border-radius:4px; margin-bottom:8px; text-align:left;font-size:25px;'>{display_value}</div>",
                            unsafe_allow_html=True)

                test_cols = st.columns(3)
                for i, field_name in enumerate(test_fields):
                    field_value = result_row[field_name]
                    display_value = str(field_value) if pd.notna(field_value) else "无数据"
                    color = "#28a745" if str(field_value).lower() == "true" else "#dc3545"
                    icon = "✅" if str(field_value).lower() == "true" else "❌"
                    with test_cols[i]:
                        st.markdown(
                            f"""
                            <div style="padding:10px; border-radius:4px; margin-bottom:8px; text-align:center;font-size:25px;">
                                <strong>{field_name}</strong>
                                <div style="color:{color}; font-size:25px; margin-top:5px;">{icon} {display_value}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
            else:
                st.markdown(
                    f"""
                    <div style="background-color:#f0f8ff; padding:10px; border-radius:0px; margin-bottom:25px;font-size:30px">
                        未找到CAS号为 {cas_input_str} 的记录
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    back_col, _ = st.columns([1, 9])
    with back_col:
        if st.button("← 返回首页"):
            goto("home")


# -------------------------
# 主控制
# -------------------------
if st.session_state.page == "home":
    page_home()
elif st.session_state.page == "map":
    page_map()
elif st.session_state.page == "cas":
    page_cas()
else:
    page_home()
