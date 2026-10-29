"""H3: H2's risk-on allocation with original portfolio-wide risk-off behavior.

No new indicator or fitted value. The standard ledger sells all tradable equity
at the next observed open following the existing SPY/SMA200 risk-off close.
"""
from research_portfolio_diversified import select_targets, risk_budget
from research_core_ledger import ResearchLedger as PortfolioLedger

MODEL='momentum-diversified-regime-research-v1'
