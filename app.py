import streamlit as st
import numpy as np
from channel_simulator import ChannelSimulator, SimParams
from air_to_air_channel import AirToAirChannel
from ai_reporter import AIReporter
from io import BytesIO
import base64

st.set_page_config(
    page_title="无人机信道模型仿真系统", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: bold; color: #1f77b4; text-align: center; margin-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">🚁 无人机信道模型仿真分析系统</p>', 
            unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ 仿真参数配置")
    
    channel_type = st.radio("信道类型", ["地空信道 (G2A)", "空空信道 (A2A)"])
    
    if channel_type == "地空信道 (G2A)":
        scenario = st.selectbox("场景类型", ["UMi-城市微小区", "UMa-城市宏小区", "RMa-农村宏小区"])
        scenario_map = {"UMi-城市微小区": "UMi", "UMa-城市宏小区": "UMa", "RMa-农村宏小区": "RMa"}
        
        col1, col2 = st.columns(2)
        with col1: h_min = st.number_input("最小高度(m)", 10, 490, 10, 10)
        with col2: h_max = st.number_input("最大高度(m)", 50, 500, 300, 10)
        if h_min >= h_max: h_max = h_min + 50
        
        col3, col4 = st.columns(2)
        with col3: d_min = st.number_input("最小距离(m)", 50, 4900, 50, 50)
        with col4: d_max = st.number_input("最大距离(m)", 100, 5000, 2000, 100)
        if d_min >= d_max: d_max = d_min + 500
        
        fc = st.slider("载频(GHz)", 0.7, 28.0, 2.0, 0.1)
        shadow_sigma = st.slider("阴影衰落标准差(dB)", 0.0, 12.0, 8.0, 0.5)
    
    else:  # A2A
        st.subheader("空空信道参数")
        h1 = st.number_input("无人机1高度(m)", 50, 500, 100, 10)
        h2 = st.number_input("无人机2高度(m)", 50, 500, 100, 10)
        v1 = st.number_input("无人机1速度(m/s)", 0, 50, 10, 1)
        v2 = st.number_input("无人机2速度(m/s)", 0, 50, 10, 1)
        fc_a2a = st.slider("空空载频(GHz)", 0.7, 28.0, 2.0, 0.1)
        d_max_a2a = st.number_input("最大空空距离(m)", 1000, 20000, 10000, 1000)
    
    st.markdown("---")
    run_btn = st.button("🚀 运行仿真", type="primary", use_container_width=True)

if run_btn:
    with st.spinner("正在进行信道仿真计算..."):
        
        if channel_type == "地空信道 (G2A)":
            params = SimParams(
                scenario=scenario_map[scenario],
                h_min=float(h_min), h_max=float(h_max),
                d_min=float(d_min), d_max=float(d_max),
                fc=float(fc), shadow_sigma=float(shadow_sigma)
            )
            
            sim = ChannelSimulator(params)
            results = sim.run()
            h_opt, p_max = sim.find_optimal_height()
            
            avg_pl = np.mean(results['PL_mean'])
            avg_cap = np.mean([c for c in results['capacity'] if c > 0])
            avg_snr = np.mean([s for s in results['SNR'] if s > -50])
            outage_rate = np.mean(results['outage_prob'])
            coverage_rate = np.mean(results['coverage_prob'])
            
            st.success(f"✅ 仿真完成！最优悬停高度为 **{h_opt:.0f}m**")
            
            cols = st.columns(5)
            cols[0].metric("最优高度", f"{h_opt:.0f}m")
            cols[1].metric("平均路径损耗", f"{avg_pl:.1f}dB")
            cols[2].metric("平均信噪比", f"{avg_snr:.1f}dB")
            cols[3].metric("信道容量", f"{avg_cap:.1f}Mbps")
            cols[4].metric("中断概率", f"{outage_rate:.1%}")
            
            st.subheader("📈 信道特性与性能分析图表")
            img = sim.generate_figures(results)
            st.image(img, use_container_width=True)
            
            img_data = img.split(',')[1]
            st.download_button("📥 下载高清图表", 
                BytesIO(base64.b64decode(img_data)).getvalue(),
                f"{scenario_map[scenario]}_simulation.png")
            
            metrics = {
                'avg_pl': avg_pl, 'avg_snr': avg_snr,
                'avg_capacity': avg_cap, 'avg_se': np.mean(results['spectral_eff']),
                'outage_rate': outage_rate, 'coverage_rate': coverage_rate,
                'pl_std': max(results['PL_std'])
            }
            reporter = AIReporter()
            report = reporter.generate_report(scenario_map[scenario], metrics, h_opt, fc)
            
            st.subheader("📊 智能分析报告")
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 20px; border-radius: 10px; color: white; line-height: 1.6;">
                {report.replace(chr(10), '<br>')}
            </div>
            """, unsafe_allow_html=True)
            
            st.download_button("📋 复制报告", report, f"Report_{scenario_map[scenario]}.txt")
        
        else:  # A2A
            a2a = AirToAirChannel(h1=h1, h2=h2, v1=v1, v2=v2, fc=fc_a2a)
            d_range = np.linspace(100, d_max_a2a, 100)
            results_a2a = a2a.simulate(d_range)
            
            st.success(f"✅ 空空信道仿真完成！")
            
            cols = st.columns(4)
            cols[0].metric("无人机1高度", f"{h1}m")
            cols[1].metric("无人机2高度", f"{h2}m")
            cols[2].metric("相对速度", f"{abs(v1-v2)}m/s")
            cols[3].metric("最大多普勒", f"{max(results_a2a['doppler_max'])/1e3:.1f}kHz")
            
            st.subheader("📈 空空信道特性图表")
            img_a2a = a2a.generate_figures(results_a2a)
            st.image(img_a2a, use_container_width=True)
            
            report_a2a = f"""【空空信道分析报告】

【链路配置】
- 无人机1: {h1}m高度, {v1}m/s速度
- 无人机2: {h2}m高度, {v2}m/s速度
- 载频: {fc_a2a}GHz
- 相对速度: {abs(v1-v2)}m/s

【信道特性】
- 主导传播: 自由空间 + 微弱大气损耗
- LoS概率: 近100%（空中环境无遮挡）
- 最大多普勒频移: {max(results_a2a['doppler_max'])/1e3:.1f}kHz
- 相干时间: {np.mean(results_a2a['coherence_time'])*1000:.2f}ms

【性能指标】
- 平均容量: {np.mean(results_a2a['capacity']):.1f}Mbps
- 覆盖范围: {d_max_a2a/1000:.1f}km（受路径损耗限制）

【关键发现】
1. 空空信道比地空信道更稳定（无建筑遮挡）
2. 多普勒效应是高速无人机的主要挑战
3. 两机高度差对路径损耗影响很小
4. 适合无人机中继和蜂群通信

【部署建议】
- 采用跟踪天线保持链路对准
- 在{fc_a2a}GHz、{abs(v1-v2)}m/s条件下实现多普勒补偿
- 根据信噪比变化采用自适应调制
"""
            st.subheader("📊 空空信道分析报告")
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 20px; border-radius: 10px; color: white; line-height: 1.6;">
                {report_a2a.replace(chr(10), '<br>')}
            </div>
            """, unsafe_allow_html=True)
            
            st.download_button("📋 复制空空报告", report_a2a, "Report_A2A.txt")

else:
    st.info("👈 **请在左侧设置参数，点击「🚀 运行仿真」开始分析**")
    st.markdown("""
    **系统功能：**
    - **地空信道(G2A)**: 3GPP UMi/UMa/RMa场景，含路径损耗、阴影衰落、性能指标
    - **空空信道(A2A)**: 自由空间主导，含多普勒分析
    - **12张专业图表**: 覆盖大尺度衰落、小尺度衰落、传输性能
    - **智能报告**: 基于规则自动生成，完全免费
    """)