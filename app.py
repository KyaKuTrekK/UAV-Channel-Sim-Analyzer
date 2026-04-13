import streamlit as st
import numpy as np
from channel_simulator import ChannelSimulator, SimParams
from ai_reporter import AIReporter
from io import BytesIO

st.set_page_config(
    page_title="3GPP无人机信道模型仿真系统", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">🚁 3GPP无人机信道模型仿真分析系统</p>', 
            unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ 仿真参数设置")
    
    scenario = st.selectbox("场景类型", ["UMi", "UMa", "RMa"])
    
    st.subheader("高度范围 (m)")
    col1, col2 = st.columns(2)
    with col1:
        h_min = st.number_input("最小", 10, 490, 10, 10)
    with col2:
        h_max = st.number_input("最大", 50, 500, 300, 10)
    
    if h_min >= h_max:
        st.error("⚠️ 最小高度必须小于最大高度！")
        h_max = h_min + 50
    
    st.subheader("距离范围 (m)")
    col3, col4 = st.columns(2)
    with col3:
        d_min = st.number_input("最小", 50, 4900, 50, 50)
    with col4:
        d_max = st.number_input("最大", 100, 5000, 2000, 100)
    
    if d_min >= d_max:
        st.error("⚠️ 最小距离必须小于最大距离！")
        d_max = d_min + 500
    
    fc = st.slider("载频 (GHz)", 0.7, 28.0, 2.0, 0.1)
    
    st.markdown("---")
    
    # AI开关
    use_ai = st.checkbox("🤖 启用AI深度分析", value=False)
    if use_ai:
        st.info("AI分析将基于仿真数据自动生成专业报告")
    
    st.markdown("---")
    run_btn = st.button("🚀 运行仿真", type="primary")

if run_btn:
    with st.spinner("正在进行信道仿真计算..."):
        params = SimParams(
            scenario=scenario,
            h_min=float(h_min),
            h_max=float(h_max),
            d_min=float(d_min),
            d_max=float(d_max),
            fc=float(fc)
        )
        
        sim = ChannelSimulator(params)
        results = sim.run()
        h_opt, p_max = sim.find_optimal_height()
        
        avg_pl = np.mean(results['PL_mean'])
        pl_range = (min(results['PL_mean']), max(results['PL_mean']))
        los_range = (min(results['LoS_prob']), max(results['LoS_prob']))
        
        st.success(f"✅ 仿真完成！最优悬停高度为 **{h_opt:.0f}m**")
        
        st.subheader("📊 关键性能指标")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("最优高度", f"{h_opt:.0f}m", f"{p_max:.1f}dB")
        with col2:
            st.metric("平均路径损耗", f"{avg_pl:.1f}dB")
        with col3:
            st.metric("LoS概率范围", f"{los_range[0]:.0%}-{los_range[1]:.0%}")
        with col4:
            st.metric("场景类型", scenario)
        
        st.subheader("📈 信道特性分析图表")
        img_base64 = sim.generate_figures(results)
        st.image(img_base64, use_container_width=True)
        
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            img_data = img_base64.split(',')[1]
            st.download_button(
                label="📥 下载高清图表 (PNG)",
                data=BytesIO(__import__('base64').b64decode(img_data)).getvalue(),
                file_name=f"{scenario}_AV_simulation.png",
                mime="image/png"
            )
        
        # 基础报告
        st.subheader("📝 基础分析报告")
        
        if scenario == "UMi":
            scene_desc, recommendation = "城市微小区（密集低矮建筑）", "建议采用中高空悬停（100-150m）"
            height_analysis = f"最优高度{h_opt:.0f}m处于建筑层之上，可有效避开地面遮挡"
        elif scenario == "UMa":
            scene_desc, recommendation = "城市宏小区（高层建筑群）", "建议采用低空飞行（<50m）或超高空（>200m）"
            height_analysis = f"最优高度{h_opt:.0f}m，{'存在低空穿透效应' if h_opt < 50 else '需超越主要建筑高度层'}"
        else:
            scene_desc, recommendation = "农村宏小区（开阔地形）", "高度灵活，建议优先保证续航时间"
            height_analysis = f"最优高度{h_opt:.0f}m，农村场景LoS概率接近100%"
        
        freq_analysis = f"{'毫米波频段覆盖受限' if fc >= 20 else 'Sub-6GHz频段覆盖良好'}"
        
        report = f"""
        ### {scenario}-AV场景信道特性分析
        
        **1. 基础参数**：{scene_desc}，载频{fc}GHz，范围{h_min}-{h_max}m/{d_min}-{d_max}m
        
        **2. 关键发现**：最优高度{h_opt:.0f}m，路径损耗{pl_range[0]:.1f}~{pl_range[1]:.1f}dB
        
        **3. 深度分析**：{height_analysis}；{freq_analysis}
        
        **4. 工程建议**：{recommendation}
        """
        st.markdown(report)
        
        # AI增强报告
        if use_ai:
            st.markdown("---")
            with st.spinner("🤖 AI正在生成深度分析..."):
                try:
                    reporter = AIReporter()
                    metrics = {
                        'avg_pl': avg_pl,
                        'los_min': los_range[0],
                        'los_max': los_range[1],
                        'avg_k': np.mean(results['K_factor']),
                        'pl_std': max(results['PL_std'])
                    }
                    ai_report = reporter.generate_report(scenario, metrics, h_opt, fc)
                    
                    st.subheader("🤖 AI智能深度分析")
                    st.info("以下内容由大语言模型基于仿真数据自动生成")
                    
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 20px;
                        border-radius: 10px;
                        color: white;
                        line-height: 1.6;
                    ">
                    {ai_report.replace(chr(10), '<br>')}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.download_button(
                        "📋 复制AI报告",
                        ai_report,
                        file_name=f"AI_Report_{scenario}.txt"
                    )
                    
                except Exception as e:
                    st.error(f"AI分析失败: {str(e)}")
                    st.info("请检查config.py中的API Key是否正确")

else:
    st.info("👈 **请在左侧设置参数，点击「🚀 运行仿真」**")
    st.image("https://via.placeholder.com/1200x600/1a1a1a/444444?text=Simulation+Results", 
             use_container_width=True)