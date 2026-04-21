import numpy as np

class PerformanceAnalyzer:
    """通信系统性能指标计算器"""
    
    def __init__(self, 
                 tx_power=23,      # dBm，无人机发射功率（典型23dBm=200mW）
                 tx_gain=0,        # dBi，发射天线增益（全向天线）
                 rx_gain=0,        # dBi，接收天线增益
                 noise_figure=5,   # dB，接收机噪声系数
                 bandwidth=20e6,     # Hz，信道带宽（20MHz LTE）
                 temp=290):        # K，环境温度（17℃）
        
        self.P_tx = tx_power
        self.G_tx = tx_gain
        self.G_rx = rx_gain
        self.NF = noise_figure
        self.B = bandwidth
        self.T = temp
        
        # 物理常数
        self.k = 1.38e-23  # 玻尔兹曼常数 J/K
        self.N_0_dBm = 10*np.log10(self.k * self.T * 1000)  # dBm/Hz
        
        # 计算噪声功率
        self.P_noise = self.N_0_dBm + 10*np.log10(self.B) + self.NF  # dBm
    
    def calculate(self, path_loss_dB, shadowing_dB=0, fading_gain_dB=0):
        """
        计算完整链路性能
        
        链路预算：P_rx = P_tx + G_tx + G_rx - PL - Shadowing + Fading
        """
        # 接收功率 (dBm)
        P_rx = self.P_tx + self.G_tx + self.G_rx - path_loss_dB - shadowing_dB + fading_gain_dB
        
        # 信噪比 (dB)
        SNR = P_rx - self.P_noise
        
        # 线性SNR
        SNR_linear = 10**(SNR/10) if SNR > -30 else 0  # 避免下溢
        
        # 信道容量 (Shannon公式，Mbps)
        if SNR_linear > 0:
            capacity = self.B * np.log2(1 + SNR_linear) / 1e6
        else:
            capacity = 0
        
        # 频谱效率 (bps/Hz)
        spectral_eff = np.log2(1 + SNR_linear) if SNR_linear > 0 else 0
        
        # 中断概率 (SNR < 0dB视为中断)
        outage = 1.0 if SNR < 0 else 0.0
        
        # 覆盖指示 (接收功率 > -100dBm)
        coverage = 1.0 if P_rx > -100 else 0.0
        
        # 调制方式建议
        if SNR > 20:
            modulation = "64QAM"
            code_rate = "3/4"
            target_ber = 1e-6
        elif SNR > 10:
            modulation = "16QAM"
            code_rate = "1/2"
            target_ber = 1e-4
        elif SNR > 0:
            modulation = "QPSK"
            code_rate = "1/2"
            target_ber = 1e-3
        else:
            modulation = "Outage"
            code_rate = "N/A"
            target_ber = 1.0
        
        return {
            'P_rx': P_rx,               # 接收功率 dBm
            'P_noise': self.P_noise,    # 噪声功率 dBm
            'SNR': SNR,                 # 信噪比 dB
            'SNR_linear': SNR_linear,   # 线性SNR
            'capacity': capacity,       # 信道容量 Mbps
            'spectral_eff': spectral_eff, # 频谱效率 bps/Hz
            'outage': outage,           # 中断指示 (0/1)
            'coverage': coverage,       # 覆盖指示 (0/1)
            'modulation': modulation,   # 建议调制方式
            'code_rate': code_rate,     # 建议编码率
            'link_margin': SNR          # 链路裕量 = SNR
        }
    
    def calculate_ber(self, SNR_dB, modulation='QPSK'):
        """理论误码率计算"""
        SNR_linear = 10**(SNR_dB/10)
        
        if modulation == 'BPSK':
            # BER = Q(sqrt(2*Eb/N0))
            ber = 0.5 * np.exp(-SNR_linear)  # 简化
        elif modulation == 'QPSK':
            # BER ≈ Q(sqrt(2*SNR))
            ber = 0.5 * np.exp(-SNR_linear/2)  # 简化近似
        elif modulation == '16QAM':
            ber = 0.75 * np.exp(-SNR_linear/5)
        elif modulation == '64QAM':
            ber = 0.875 * np.exp(-SNR_linear/10)
        else:
            ber = 0.5
        
        return min(ber, 0.5)  # 上限0.5