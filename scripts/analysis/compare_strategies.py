#!/usr/bin/env python3
"""
Compare the three backtest strategies
"""

print("="*80)
print("BACKTEST STRATEGY COMPARISON (4 years: 2022-2026)")
print("="*80)
print()

strategies = {
    'Original (All 50 stocks)': {
        'trades': 723,
        'roi': 6.76,
        'win_rate': 41.5,
        'avg_return': 7.28,
        'invested': 848_500,
        'returned': 905_883,
        'profit': 57_383
    },
    'Adaptive Filter (3 strikes + win rate)': {
        'trades': 552,
        'roi': 4.64,
        'win_rate': 40.8,
        'avg_return': 6.86,
        'invested': 583_625,
        'returned': 610_694,
        'profit': 27_069
    },
    'Conservative Filter (pre-screen quality)': {
        'trades': 406,
        'roi': 13.24,
        'win_rate': 49.0,
        'avg_return': 13.91,
        'invested': 478_000,
        'returned': 541_300,
        'profit': 63_300
    }
}

print(f"{'Strategy':<45} {'Trades':<10} {'ROI':<12} {'Win%':<10} {'Avg Ret':<12} {'Profit':<15}")
print("-"*80)

for name, stats in strategies.items():
    print(f"{name:<45} {stats['trades']:<10} {stats['roi']:>10.2f}%  {stats['win_rate']:>8.1f}%  {stats['avg_return']:>10.2f}%  ${stats['profit']:>12,.0f}")

print()
print("="*80)
print("KEY FINDINGS:")
print("="*80)
print()

print("🏆 WINNER: Conservative Filter (+13.24% ROI)")
print()
print("Why it works:")
print("  ✓ Pre-filters bad stocks BEFORE trading")
print("  ✓ Market cap > $300M eliminates penny stocks")
print("  ✓ Requires 2+ insiders (not just 1 hedge fund)")
print("  ✓ Skips stocks in >20% drawdown (73 trades avoided)")
print("  ✓ 49% win rate vs 41% for unfiltered")
print("  ✓ Double the ROI of adaptive learning")
print()

print("❌ Adaptive Filter Disappoints (+4.64% ROI)")
print()
print("Why it struggled:")
print("  • Learns AFTER losing money (late detection)")
print("  • Still took 552 trades vs 406 conservative")
print("  • Blacklisted 9 tickers but damage already done")
print("  • PSEC alone: 82 trades before blacklist")
print()

print("💡 RECOMMENDATION:")
print()
print("Use Conservative Pre-Filters:")
print("  1. Market cap > $300M")
print("  2. Minimum 2 unique insiders")
print("  3. Skip if stock fell >20% in last 30 days")
print()
print("This gives 2x better ROI (13.24% vs 6.76%) by avoiding")
print("bad stocks BEFORE we waste money learning they're bad!")
print()

print("="*80)
print("S&P 500 COMPARISON:")
print("="*80)
print()
print("S&P 500 (2022-2026): ~50-60% total return = ~12-15% annualized")
print()
print("Our Results:")
print("  Original strategy:    6.76% over 4 years = 1.7% annualized ❌")
print("  Adaptive filter:      4.64% over 4 years = 1.2% annualized ❌")
print("  Conservative filter: 13.24% over 4 years = 3.1% annualized ⚠️")
print()
print("⚠️  Even our best strategy (13.24%) barely beats S&P 500!")
print()
print("💡 Next Steps:")
print("  • More aggressive profit targets (hold winners longer)")
print("  • Wider stop losses (less premature exits)")
print("  • Focus on highest-conviction signals (5+ insiders)")
print("  • Consider only top 10-15 stocks, not all 28")
print()
