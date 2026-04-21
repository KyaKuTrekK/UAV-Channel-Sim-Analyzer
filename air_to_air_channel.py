import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Literal
import io
import base64
import os
from performance_metrics import PerformanceAnalyzer

# ========== 中文字体配置（宋体） ==========
current_dir = os.path.dirname(os.path.abspath(__file__))
font_path = os.path.join(current_dir, 'fonts', 'NotoSerifSC[wght].ttf')

if os.path.exists(font_path):
    from matplotlib import font_manager
    font_manager.fontManager.addfont(font_path)
    plt.rcParams['font.family'] = 'Noto Serif SC'
    print(f"✅ 宋体加载成功: {font_path}")
else:
    # 本地备用
    plt.rcParams['font.sans-serif'] = ['SimSun', '宋体', 'SimHei', 'DejaVu Sans']
    print("⚠️ 使用系统备用字体")

plt.rcParams['axes.unicode_minus'] = False

class AirToAirChannel:
    """空空信道模型（无人机对无人机）"""
    
    def __init__(self, h1=100, h2=100, v1=10, v2=10, fc=2.0):
        self.h1 = h1
        self.h2 = h2
        self.v1 = v1
        self.v2 = v2
        self.fc = fc
        self.c = 3e8
        
        self.perf = PerformanceAnalyzer(tx_power=23, bandwidth=20e6)
    
    def pathloss(self, d_horiz):
        d_3D = np.sqrt(d_horiz**2 + (self.h1 - self.h2)**2)
        fspl = 20*np.log10(d_3D) + 20*np.log10(self.fc) + 92.45
        h_avg = (self.h1 + self.h2) / 2
        atm_loss = 0.01 * (d_3D/1000) * max(0, (1 - h_avg/10000))
        return fspl + atm_loss
    
    def los_probability(self):
        return 1.0
    
    def doppler_shift(self, d_horiz):
        v_rel = abs(self.v1 - self.v2)
        f_d_max = v_rel * self.fc * 1e9 / self.c
        return f_d_max
    
    def coherence_time(self):
        f_d = self.doppler_shift(1000)
        if f_d > 0:
            return 1 / (2 * f_d)
        return np.inf
    
    def simulate(self, d_range):
        results = {
            'distance': [],
            'PL': [],
            'P_rx': [],
            'SNR': [],
            'capacity': [],
            'doppler_max': [],
            'coherence_time': []
        }
        
        for d in d_range:
            pl = self.pathloss(d)
            perf = self.perf.calculate(pl)
            fd = self.doppler_shift(d)
            tc = self.coherence_time() if fd > 0 else np.inf
            
            results['distance'].append(d)
            results['PL'].append(pl)
            results['P_rx'].append(perf['P_rx'])
            results['SNR'].append(perf['SNR'])
            results['capacity'].append(perf['capacity'])
            results['doppler_max'].append(fd)
            results['coherence_time'].append(tc)
        
        return results
    
    def generate_figures(self, results):
        fig, axes = plt.subplots(2, 3, figsize=(15, 10), facecolor='black')
        
        # 图1: 路径损耗
        ax = axes[0,0]
        ax.set_facecolor('black')
        ax.plot(np.array(results['distance'])/1000, results['PL'], 'cyan', linewidth=2)
        ax.set_xlabel('距离 (km)', color='white')
        ax.set_ylabel('路径损耗 (dB)', color='white')
        ax.set_title('空空路径损耗 (自由空间)', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图2: 接收功率
        ax = axes[0,1]
        ax.set_facecolor('black')
        ax.plot(np.array(results['distance'])/1000, results['P_rx'], 'green', linewidth=2)
        ax.set_xlabel('距离 (km)', color='white')
        ax.set_ylabel('接收功率 (dBm)', color='white')
        ax.set_title('空空接收功率', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图3: 容量
        ax = axes[0,2]
        ax.set_facecolor('black')
        ax.plot(np.array(results['distance'])/1000, results['capacity'], 'yellow', linewidth=2)
        ax.set_xlabel('距离 (km)', color='white')
        ax.set_ylabel('信道容量 (Mbps)', color='white')
        ax.set_title('空空信道容量', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图4: 多普勒频移
        ax = axes[1,0]
        ax.set_facecolor('black')
        ax.plot(np.array(results['distance'])/1000, np.array(results['doppler_max'])/1e3, 'red', linewidth=2)
        ax.set_xlabel('距离 (km)', color='white')
        ax.set_ylabel('多普勒频移 (kHz)', color='white')
        ax.set_title('最大多普勒频移', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图5: 相干时间
        ax = axes[1,1]
        ax.set_facecolor('black')
        tc_ms = np.array(results['coherence_time']) * 1000
        ax.plot(np.array(results['distance'])/1000, tc_ms, 'magenta', linewidth=2)
        ax.set_xlabel('距离 (km)', color='white')
        ax.set_ylabel('相干时间 (ms)', color='white')
        ax.set_title('信道相干时间', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图6: SNR
        ax = axes[1,2]
        ax.set_facecolor('black')
        ax.plot(np.array(results['distance'])/1000, results['SNR'], 'lime', linewidth=2, label='空空链路')
        ax.set_xlabel('距离 (km)', color='white')
        ax.set_ylabel('信噪比 (dB)', color='white')
        ax.set_title('空空链路SNR性能', color='white')
        ax.legend()
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, facecolor='black', 
                    edgecolor='none', bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode()
        plt.close(fig)
        
        return f"data:image/png;base64,{img_base64}"