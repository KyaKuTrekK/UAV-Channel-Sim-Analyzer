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
font_path = os.path.join(current_dir, 'fonts', 'NotoSerifSC-Regular.ttf')

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
@dataclass
class SimParams:
    scenario: Literal["UMi", "UMa", "RMa"]
    h_min: float = 10
    h_max: float = 300
    d_min: float = 50
    d_max: float = 2000
    fc: float = 2.0
    shadow_sigma: float = 8.0

class ChannelSimulator:
    def __init__(self, params: SimParams):
        self.p = params
        self.h_range = np.linspace(params.h_min, params.h_max, 50)
        self.d_range = np.linspace(params.d_min, params.d_max, 50)
        self.perf = PerformanceAnalyzer(tx_power=23, bandwidth=20e6 if params.fc < 6 else 100e6)
    
    def run(self):
        results = {
            'PL_mean': [], 'PL_std': [], 'LoS_prob': [], 'PL_dist': None,
            'PL_height': {}, 'power_expect': {}, 'K_factor': [],
            'shadowing': [], 'P_rx': [], 'SNR': [], 'capacity': [],
            'spectral_eff': [], 'outage_prob': [], 'coverage_prob': [],
            'modulation': []
        }
        
        h_fix = 100
        for d in self.d_range:
            pl_los = self._pathloss(d, h_fix, True)
            pl_nlos = self._pathloss(d, h_fix, False)
            p_los = self._los_prob(d, h_fix)
            pl_expect = p_los * pl_los + (1-p_los) * pl_nlos
            shadow = np.random.normal(0, self.p.shadow_sigma)
            PL_total = pl_expect + shadow
            perf = self.perf.calculate(PL_total)
            
            results['PL_mean'].append(pl_expect)
            results['PL_std'].append(self.p.shadow_sigma * np.sqrt(p_los*(1-p_los)))
            results['LoS_prob'].append(p_los)
            results['shadowing'].append(shadow)
            results['P_rx'].append(perf['P_rx'])
            results['SNR'].append(perf['SNR'])
            results['capacity'].append(perf['capacity'])
            results['spectral_eff'].append(perf['spectral_eff'])
            results['outage_prob'].append(perf['outage'])
            results['coverage_prob'].append(perf['coverage'])
            results['modulation'].append(perf['modulation'])
        
        d_target = 500
        samples = []
        for _ in range(1000):
            is_los = np.random.random() < self._los_prob(d_target, h_fix)
            pl = self._pathloss(d_target, h_fix, is_los)
            shadow = np.random.normal(0, self.p.shadow_sigma)
            samples.append(pl + shadow)
        results['PL_dist'] = samples
        
        for h in self.h_range:
            p_los_rep = self._los_prob(600, h)
            k = 20 + 0.1 * h + 30 * p_los_rep
            results['K_factor'].append(k)
            
            for d in [200, 600, 1000]:
                pl_los = self._pathloss(d, h, True)
                pl_nlos = self._pathloss(d, h, False)
                p_los = self._los_prob(d, h)
                pl_exp = p_los * pl_los + (1-p_los) * pl_nlos
                if d not in results['PL_height']:
                    results['PL_height'][d] = []
                    results['power_expect'][d] = []
                results['PL_height'][d].append(pl_exp)
                results['power_expect'][d].append(-pl_exp)
        
        return results
    
    def _pathloss(self, d2D, h_UT, los):
        d3D = np.sqrt(d2D**2 + h_UT**2)
        fc = self.p.fc
        if self.p.scenario == "UMi":
            if los:
                return 28.0 + 22*np.log10(d3D) + 20*np.log10(fc)
            else:
                return 32.4 + 20*np.log10(fc) + 31.9*np.log10(d3D)
        elif self.p.scenario == "UMa":
            if los:
                return 28.0 + 22*np.log10(d3D) + 20*np.log10(fc)
            else:
                return 32.4 + 20*np.log10(fc) + 30*np.log10(d3D)
        else:
            return 28.0 + 22*np.log10(d3D) + 20*np.log10(fc)
    
    def _los_prob(self, d2D, h_UT):
        d2D_km = d2D / 1000
        if self.p.scenario == "UMi":
            if h_UT <= 22.5:
                return max(0.01, 1 - 0.5*d2D_km)
            else:
                return max(0.01, 1 - 0.3*d2D_km)
        elif self.p.scenario == "UMa":
            return max(0.01, 1 - 0.2*d2D_km)
        else:
            return 1.0
    
    def find_optimal_height(self, d_target=600):
        power = []
        for h in self.h_range:
            pl_los = self._pathloss(d_target, h, True)
            pl_nlos = self._pathloss(d_target, h, False)
            p_los = self._los_prob(d_target, h)
            pl_exp = p_los * pl_los + (1-p_los) * pl_nlos
            power.append(-pl_exp)
        idx = np.argmax(power)
        return self.h_range[idx], power[idx]
    
    def generate_figures(self, results):
        fig, axes = plt.subplots(3, 4, figsize=(20, 15), facecolor='black')
        
        # 图1: 路径损耗vs距离
        ax = axes[0,0]
        ax.set_facecolor('black')
        ax.plot(self.d_range/1000, results['PL_mean'], 'b-', linewidth=2, label='均值')
        ax.fill_between(self.d_range/1000, 
                       np.array(results['PL_mean'])-np.array(results['PL_std']),
                       np.array(results['PL_mean'])+np.array(results['PL_std']),
                       alpha=0.3, color='red', label='阴影衰落')
        ax.set_xlabel('水平距离 d₂D (km)', color='white')
        ax.set_ylabel('路径损耗 (dB)', color='white')
        ax.set_title(f'{self.p.scenario}-AV: 路径损耗 vs 距离 (h=100m)', color='white')
        ax.legend()
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图2: LoS概率
        ax = axes[0,1]
        ax.set_facecolor('black')
        ax.plot(self.d_range/1000, results['LoS_prob'], 'lime', linewidth=2)
        ax.set_xlabel('水平距离 d₂D (km)', color='white')
        ax.set_ylabel('LoS概率', color='white')
        ax.set_title(f'{self.p.scenario}-AV: LoS概率 (h=100m)', color='white')
        ax.set_ylim(0, 1)
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图3: 路径损耗分布
        ax = axes[0,2]
        ax.set_facecolor('black')
        ax.hist(results['PL_dist'], bins=30, density=True, alpha=0.7, 
                color='steelblue', edgecolor='white')
        ax.set_xlabel('路径损耗 (dB)', color='white')
        ax.set_ylabel('概率密度', color='white')
        ax.set_title('d=500m处路径损耗分布', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图4: 阴影衰落
        ax = axes[0,3]
        ax.set_facecolor('black')
        ax.plot(self.d_range/1000, results['shadowing'], 'orange', alpha=0.7)
        ax.axhline(y=0, color='white', linestyle='--', alpha=0.5)
        ax.set_xlabel('水平距离 (km)', color='white')
        ax.set_ylabel('阴影衰落 (dB)', color='white')
        ax.set_title(f'对数正态阴影衰落 (σ={self.p.shadow_sigma}dB)', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图5: 多高度对比
        ax = axes[1,0]
        ax.set_facecolor('black')
        colors = ['蓝色', '青色', '黄色']
        labels = ['d=200m', 'd=600m', 'd=1000m']
        for i, (d_val, color, label) in enumerate(zip([200, 600, 1000], ['blue', 'cyan', 'yellow'], labels)):
            if d_val in results['PL_height']:
                ax.plot(self.d_range/1000, results['PL_height'][d_val], 
                       color=color, linewidth=2, label=label)
        ax.set_xlabel('水平距离 d₂D (km)', color='white')
        ax.set_ylabel('期望路径损耗 (dB)', color='white')
        ax.set_title('不同高度下的期望路径损耗对比', color='white')
        ax.legend()
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图6: 最优高度
        ax = axes[1,1]
        ax.set_facecolor('black')
        colors = ['#3498db', '#e67e22', '#f1c40f']
        labels = ['d=200m', 'd=600m', 'd=1000m']
        for d_val, color, label in zip([200, 600, 1000], colors, labels):
            if d_val in results['power_expect']:
                ax.plot(self.h_range, results['power_expect'][d_val], 
                       color=color, linewidth=2.5, label=label)
                idx = np.argmax(results['power_expect'][d_val])
                ax.scatter(self.h_range[idx], results['power_expect'][d_val][idx], 
                          s=150, color=color, zorder=5, edgecolors='white', linewidth=2)
                ax.annotate(f'h最优={self.h_range[idx]:.0f}m', 
                           xy=(self.h_range[idx], results['power_expect'][d_val][idx]),
                           xytext=(10, 10), textcoords='offset points',
                           color=color, fontsize=10, fontweight='bold')
        ax.set_xlabel('无人机高度 hᵤₜ (m)', color='white')
        ax.set_ylabel('信道功率期望 (dB)', color='white')
        ax.set_title('功率期望 vs 高度 (存在最优高度)', color='white')
        ax.legend()
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图7: K因子
        ax = axes[1,2]
        ax.set_facecolor('black')
        ax.plot(self.h_range, results['K_factor'], 'magenta', linewidth=2)
        ax.set_xlabel('无人机高度 hᵤₜ (m)', color='white')
        ax.set_ylabel('莱斯K因子 (dB)', color='white')
        ax.set_title('小尺度衰落: K因子 vs 高度', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图8: 快衰落包络
        ax = axes[1,3]
        ax.set_facecolor('black')
        x = np.linspace(0, 3, 100)
        rayleigh = x * np.exp(-x**2/2)
        K = 10
        from scipy.special import i0
        rician = x * np.exp(-(x**2 + K)/2) * i0(x*np.sqrt(2*K))
        
        ax.plot(x, rayleigh, 'cyan', linewidth=2, label='瑞利 (NLoS)')
        ax.plot(x, rician, 'yellow', linewidth=2, label=f'莱斯 K={K}dB (LoS)')
        ax.set_xlabel('归一化包络', color='white')
        ax.set_ylabel('概率密度', color='white')
        ax.set_title('快衰落包络分布', color='white')
        ax.legend()
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图9: 接收功率
        ax = axes[2,0]
        ax.set_facecolor('black')
        ax.plot(self.d_range/1000, results['P_rx'], 'green', linewidth=2)
        ax.axhline(y=-100, color='red', linestyle='--', alpha=0.7, label='覆盖门限')
        ax.set_xlabel('水平距离 (km)', color='white')
        ax.set_ylabel('接收功率 (dBm)', color='white')
        ax.set_title('接收功率 vs 距离', color='white')
        ax.legend()
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图10: SNR
        ax = axes[2,1]
        ax.set_facecolor('black')
        ax.plot(self.d_range/1000, results['SNR'], 'yellow', linewidth=2)
        ax.axhline(y=0, color='red', linestyle='--', alpha=0.7, label='中断门限')
        ax.fill_between(self.d_range/1000, results['SNR'], 0, 
                       where=np.array(results['SNR'])<0, alpha=0.3, color='red')
        ax.set_xlabel('水平距离 (km)', color='white')
        ax.set_ylabel('信噪比 (dB)', color='white')
        ax.set_title('信噪比 SNR', color='white')
        ax.legend()
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图11: 信道容量
        ax = axes[2,2]
        ax.set_facecolor('black')
        ax.plot(self.d_range/1000, results['capacity'], 'white', linewidth=2)
        ax.fill_between(self.d_range/1000, 0, results['capacity'], alpha=0.3, color='green')
        ax.set_xlabel('水平距离 (km)', color='white')
        ax.set_ylabel('信道容量 (Mbps)', color='white')
        ax.set_title(f'信道容量 ({self.p.fc}GHz, {self.perf.B/1e6}MHz)', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图12: SNR累积分布
        ax = axes[2,3]
        ax.set_facecolor('black')
        snr_sorted = np.sort(results['SNR'])
        cdf = np.arange(1, len(snr_sorted)+1) / len(snr_sorted)
        ax.plot(snr_sorted, cdf, 'lime', linewidth=2)
        ax.axvline(x=0, color='red', linestyle='--', alpha=0.7, label='中断边界')
        ax.set_xlabel('信噪比 (dB)', color='white')
        ax.set_ylabel('累积概率', color='white')
        ax.set_title('SNR累积分布函数', color='white')
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