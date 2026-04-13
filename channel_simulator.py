import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Literal
import io
import base64

@dataclass
class SimParams:
    scenario: Literal["UMi", "UMa", "RMa"]
    h_min: float = 10
    h_max: float = 300
    d_min: float = 50
    d_max: float = 2000
    fc: float = 2.0
    use_ml: bool = False

class ChannelSimulator:
    def __init__(self, params: SimParams):
        self.p = params
        self.h_range = np.linspace(params.h_min, params.h_max, 50)
        self.d_range = np.linspace(params.d_min, params.d_max, 50)
        
    def run(self):
        results = {
            'PL_mean': [],
            'PL_std': [],
            'LoS_prob': [],
            'PL_dist': None,
            'PL_height': {},
            'power_expect': {},
            'K_factor': []
        }
        
        h_fix = 100
        for d in self.d_range:
            pl_los = self._pathloss(d, h_fix, True)
            pl_nlos = self._pathloss(d, h_fix, False)
            p_los = self._los_prob(d, h_fix)
            
            pl_expect = p_los * pl_los + (1-p_los) * pl_nlos
            results['PL_mean'].append(pl_expect)
            
            var = p_los*(pl_los-pl_expect)**2 + (1-p_los)*(pl_nlos-pl_expect)**2
            results['PL_std'].append(np.sqrt(max(var, 0)))
            results['LoS_prob'].append(p_los)
        
        d_target = 500
        samples = []
        for _ in range(1000):
            is_los = np.random.random() < self._los_prob(d_target, h_fix)
            pl = self._pathloss(d_target, h_fix, is_los) + np.random.normal(0, 4)
            samples.append(pl)
        results['PL_dist'] = samples
        
        for h in self.h_range:
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
        
        for h in self.h_range:
            p_los = self._los_prob(500, h)
            k = 20 + 0.1 * h + 30 * p_los
            results['K_factor'].append(k)
        
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
        fig, axes = plt.subplots(2, 3, figsize=(16, 10), facecolor='black')
        d_range = self.d_range
        
        # 图1
        ax = axes[0,0]
        ax.set_facecolor('black')
        ax.plot(d_range/1000, results['PL_mean'], 'b-', linewidth=2, label='均值')
        ax.fill_between(d_range/1000, 
                       np.array(results['PL_mean'])-np.array(results['PL_std']),
                       np.array(results['PL_mean'])+np.array(results['PL_std']),
                       alpha=0.3, color='red', label='±1标准差')
        ax.set_xlabel('水平距离 d₂D (km)', color='white')
        ax.set_ylabel('路径损耗 (dB)', color='white')
        ax.set_title(f'{self.p.scenario}-AV: 路径损耗 vs 距离 (h=100m)', color='white')
        ax.legend()
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图2
        ax = axes[0,1]
        ax.set_facecolor('black')
        ax.plot(d_range/1000, results['LoS_prob'], 'lime', linewidth=2)
        ax.set_xlabel('水平距离 d₂D (km)', color='white')
        ax.set_ylabel('LoS概率', color='white')
        ax.set_title(f'{self.p.scenario}-AV: LoS概率 (h=100m)', color='white')
        ax.set_ylim(0, 1)
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图3
        ax = axes[0,2]
        ax.set_facecolor('black')
        ax.hist(results['PL_dist'], bins=30, density=True, alpha=0.7, 
                color='steelblue', edgecolor='white')
        ax.set_xlabel('路径损耗 (dB)', color='white')
        ax.set_ylabel('概率密度', color='white')
        ax.set_title(f'd=500m处路径损耗分布', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图4
        ax = axes[1,0]
        ax.set_facecolor('black')
        colors = ['blue', 'cyan', 'yellow']
        labels = ['d=200m', 'd=600m', 'd=1000m']
        for d_val, color, label in zip([200, 600, 1000], colors, labels):
            if d_val in results['PL_height']:
                ax.plot(d_range/1000, results['PL_height'][d_val], 
                       color=color, linewidth=2, label=label)
        ax.set_xlabel('水平距离 d₂D (km)', color='white')
        ax.set_ylabel('期望路径损耗 (dB)', color='white')
        ax.set_title('不同高度下的期望路径损耗对比', color='white')
        ax.legend()
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图5
        ax = axes[1,1]
        ax.set_facecolor('black')
        colors = ['#3498db', '#e67e22', '#f1c40f']
        for d_val, color, label in zip([200, 600, 1000], colors, labels):
            if d_val in results['power_expect']:
                ax.plot(self.h_range, results['power_expect'][d_val], 
                       color=color, linewidth=2.5, label=label)
                idx = np.argmax(results['power_expect'][d_val])
                ax.scatter(self.h_range[idx], results['power_expect'][d_val][idx], 
                          s=150, color=color, zorder=5, edgecolors='white', linewidth=2)
                ax.annotate(f'hₒₚₜ={self.h_range[idx]:.0f}m', 
                           xy=(self.h_range[idx], results['power_expect'][d_val][idx]),
                           xytext=(10, 10), textcoords='offset points',
                           color=color, fontsize=11, fontweight='bold')
        ax.set_xlabel('无人机高度 hᵤₜ (m)', color='white')
        ax.set_ylabel('信道功率期望 (dB)', color='white')
        ax.set_title('功率期望 vs 高度 (存在最优高度)', color='white')
        ax.legend()
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # 图6
        ax = axes[1,2]
        ax.set_facecolor('black')
        ax.plot(self.h_range, results['K_factor'], 'magenta', linewidth=2)
        ax.set_xlabel('无人机高度 hᵤₜ (m)', color='white')
        ax.set_ylabel('莱斯K因子 (dB)', color='white')
        ax.set_title('小尺度衰落: K因子 vs 高度', color='white')
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