import matplotlib.pyplot as plt
import pandas as pd
import os

class Plotter:
    def __init__(self, df: pd.DataFrame, out_dir: str):
        self.df = df
        self.out_dir = out_dir
        os.makedirs(out_dir, exist_ok=True)
        
    def plot_success_rate(self):
        grouped = self.df.groupby('agent')['success'].mean()
        plt.figure(figsize=(6, 4))
        grouped.plot(kind='bar', color=['red', 'green'])
        plt.title('RCA Success Rate: Baseline vs Constrained')
        plt.ylabel('Success Rate')
        plt.ylim(0, 1.0)
        plt.tight_layout()
        plt.savefig(os.path.join(self.out_dir, 'success_rate.png'))
        plt.close()
        
    def plot_tool_calls(self):
        grouped = self.df.groupby('agent')['tool_calls'].mean()
        plt.figure(figsize=(6, 4))
        grouped.plot(kind='bar', color=['blue', 'cyan'])
        plt.title('Average Tool Calls per Bug')
        plt.ylabel('Tool Calls')
        plt.tight_layout()
        plt.savefig(os.path.join(self.out_dir, 'tool_calls.png'))
        plt.close()

    def generate_all(self):
        self.plot_success_rate()
        self.plot_tool_calls()
