import openai
import os

class AIReporter:
    """AI报告生成器"""
    
    def __init__(self, api_key=None):
        # 优先级：传入参数 > 环境变量 > 本地配置文件
        self.api_key = (
            api_key or
            os.getenv("OPENROUTER_API_KEY") or
            self._load_from_config() or
            None
        )
        
        if not self.api_key:
            raise ValueError("未找到API Key，请在config.py中配置")
        
        self.client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key
        )
    
    def _load_from_config(self):
        try:
            from config import API_KEY
            return API_KEY
        except:
            return None
    
    def generate_report(self, scenario, metrics, optimal_h, fc):
        prompt = f"""你是一位无线通信专家，撰写3GPP无人机信道模型毕业设计论文分析。

基于以下数据撰写技术分析（300字），包含机理分析和工程建议：

场景：{scenario}-AV（{'城市微小区' if scenario=='UMi' else '城市宏小区' if scenario=='UMa' else '农村宏小区'}）
最优高度：{optimal_h:.0f}m
载频：{fc}GHz
平均路径损耗：{metrics['avg_pl']:.1f}dB
LoS概率范围：{metrics['los_min']:.0%}-{metrics['los_max']:.0%}
莱斯K因子：{metrics['avg_k']:.1f}dB

要求学术化表达，分点论述。"""

        try:
            response = self.client.chat.completions.create(
                model="google/gemma-4-31b-it:free",
                messages=[
                    {"role": "system", "content": "你是严谨的无线通信研究者，擅长信道建模。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=600
            )
            return response.choices[0].message.content
            
        except Exception as e:
            return f"AI分析失败: {str(e)}"