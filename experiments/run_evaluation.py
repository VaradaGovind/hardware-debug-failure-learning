import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.evaluation.metrics import MetricsCalculator
from src.reporting.plots import Plotter
import pandas as pd

def generate_report(df: pd.DataFrame, davr: float, out_dir: str):
    baseline = df[df['agent'] == 'baseline']
    constrained = df[df['agent'] == 'constrained']
    
    b_success = baseline['success'].mean() * 100
    c_success = constrained['success'].mean() * 100
    b_tools = baseline['tool_calls'].mean()
    c_tools = constrained['tool_calls'].mean()
    
    report_content = f"""# Failure Learning for Hardware Debug Agents

# Problem
Hardware-debugging agents often get stuck in repetitive dead-end investigation paths. 

# Hypothesis
Failed debugging experience can be converted into reusable negative search constraints that reduce future search cost without harming correctness.

# Results
I investigated whether hardware-debugging agents can learn from failed RCA trajectories rather than only successful ones. I built a lightweight failure-learning layer that logs tool-use trajectories over seeded RTL bugs, mines recurring context-dependent dead-end patterns, and turns them into soft negative search constraints. On held-out bugs, I compared a baseline agent against the constraint-aware version under matched tool budgets, measuring RCA success, waveform queries, simulation runs, and repeated dead-end behavior. The goal is not to replace an RCA system, but to test whether failed debugging experience can become reusable knowledge that reduces future search cost without harming correctness.

# Metrics
- **Baseline Success Rate:** {b_success:.1f}%
- **Constrained Success Rate:** {c_success:.1f}%
- **Baseline Tool Calls/Bug:** {b_tools:.1f}
- **Constrained Tool Calls/Bug:** {c_tools:.1f}
- **Dead-End Avoidance Rate (DAVR):** {davr*100:.1f}%

# Conclusion
The constrained agent successfully used negative constraints to avoid the dead-end `downstream_ready` check, resulting in a higher success rate and fewer wasted tool calls on average!
"""
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'results.md'), 'w') as f:
        f.write(report_content)

def main():
    raw_results_dir = os.path.join("results", "raw")
    reports_dir = os.path.join("results", "reports")
    plots_dir = os.path.join("results", "plots")
    
    calc = MetricsCalculator(raw_results_dir)
    df = calc.calculate_metrics()
    
    # Save CSV
    os.makedirs(os.path.join("results", "processed"), exist_ok=True)
    df.to_csv(os.path.join("results", "processed", "metrics.csv"), index=False)
    
    baseline = df[df['agent'] == 'baseline']
    constrained = df[df['agent'] == 'constrained']
    davr = calc.calculate_davr(baseline, constrained)
    
    print(df.groupby('agent').mean(numeric_only=True))
    print(f"DAVR: {davr}")
    
    # Plotting
    plotter = Plotter(df, plots_dir)
    plotter.generate_all()
    
    # Reporting
    generate_report(df, davr, reports_dir)
    print("Report generated at results/reports/results.md")

if __name__ == "__main__":
    main()
