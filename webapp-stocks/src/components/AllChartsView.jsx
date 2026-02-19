import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as ChartTooltip, ResponsiveContainer, Area, AreaChart, ComposedChart, Scatter, ReferenceDot, Customized } from 'recharts';

// Utility function to format amounts with K/M notation
const formatAmount = (amount) => {
  if (amount === null || amount === undefined || isNaN(amount)) return 'N/A';
  const num = parseFloat(amount);
  if (num >= 1000000) {
    return `$${(num / 1000000).toFixed(1)}M`;
  } else if (num >= 1000) {
    return `$${(num / 1000).toFixed(1)}K`;
  } else {
    return `$${num.toFixed(0)}`;
  }
};

const AllChartsView = ({ stocks, backtestTrades }) => {
  console.log('🟢 [AllChartsView] Component rendered');
  console.log('🟢 [AllChartsView] stocks prop:', stocks?.length || 0, 'stocks');
  console.log('🟢 [AllChartsView] backtestTrades prop:', backtestTrades?.length || 0, 'trades');
  if (backtestTrades?.length > 0) {
    console.log('🟢 [AllChartsView] Sample backtestTrade:', backtestTrades[0]);
  }
  
  const [allBacktestTrades, setAllBacktestTrades] = useState(null);
  
  // Fetch backtest results ONCE for all stocks (unless provided via prop)
  useEffect(() => {
    if (backtestTrades) {
      setAllBacktestTrades(backtestTrades);
      return;
    }
    
    // Otherwise fetch from default endpoint
    const fetchBacktestResults = async () => {
      try {
        const cacheBuster = new Date().getTime();
        const url = `http://localhost:3001/api/backtest-results?_=${cacheBuster}`;
        
        const response = await fetch(url, {
          cache: 'no-store',
          headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
          }
        });
        
        const data = await response.json();
        
        if (data.success && data.trades) {
          setAllBacktestTrades(data.trades);
        }
      } catch (err) {
        console.error('Failed to fetch backtest results:', err);
      }
    };
    
    fetchBacktestResults();
  }, [backtestTrades]);
  
  return (
    <div className="grid grid-cols-1 gap-8">
      {stocks.map((stock) => (
        <SingleStockChart 
          key={stock.ticker} 
          ticker={stock.ticker} 
          allBacktestTrades={allBacktestTrades}
        />
      ))}
    </div>
  );
};

const SingleStockChart = ({ ticker, allBacktestTrades }) => {
  const [stockHistory, setStockHistory] = useState(null);
  const [insiderTrades, setInsiderTrades] = useState(null);
  const [loading, setLoading] = useState(true);
  const [insiderLoading, setInsiderLoading] = useState(true);
  const [error, setError] = useState(null);
  const [period, setPeriod] = useState('1y'); // Default to 1 year
  const [focusDate, setFocusDate] = useState(''); // Empty by default
  
  // Filter backtest trades for this ticker
  const backtestTrades = allBacktestTrades ? allBacktestTrades.filter(trade => trade.ticker === ticker) : null;
  
  // DEBUG: Log trade filtering (once per ticker)
  useEffect(() => {
    console.log(`🟢 [StockChart] ${ticker}: Filtering trades from allBacktestTrades (${allBacktestTrades?.length || 0} total)`);
    console.log(`🟢 [StockChart] ${ticker}: Found ${backtestTrades?.length || 0} trades for this ticker`);
    if (backtestTrades?.length > 0) {
      console.log(`🟢 [StockChart] ${ticker}: Sample trade:`, backtestTrades[0]);
    }
  }, [ticker, allBacktestTrades]);
  
  // DEBUG: GROV-specific debugging
  useEffect(() => {
    if (ticker === 'GROV' && allBacktestTrades) {
      console.log('🔍 GROV DEBUG:');
      console.log('  Total trades in allBacktestTrades:', allBacktestTrades.length);
      const grovTrades = allBacktestTrades.filter(t => t.ticker === 'GROV');
      console.log('  GROV trades found:', grovTrades.length);
      grovTrades.forEach((trade, idx) => {
        console.log(`  Trade ${idx + 1}:`, {
          entry_date: trade.entry_date,
          entry_price: trade.entry_price,
          exit_date: trade.exit_date,
          return_pct: trade.return_pct
        });
      });
    }
  }, [allBacktestTrades, ticker]);

  useEffect(() => {
    if (focusDate) {
      if (!stockHistory?.history) {
        fetchStockHistory('max');
        return;
      }
      
      const firstAvailableDate = new Date(stockHistory.history[0].date.split('T')[0].split(' ')[0] + 'T12:00:00Z');
      const lastAvailableDate = new Date(stockHistory.history[stockHistory.history.length - 1].date.split('T')[0].split(' ')[0] + 'T12:00:00Z');
      const targetDate = new Date(focusDate + 'T12:00:00Z');
      
      if (targetDate < firstAvailableDate || targetDate > lastAvailableDate) {
        fetchStockHistory('max');
        return;
      }
      
      return;
    }
    
    fetchStockHistory(period);
  }, [period, ticker, focusDate]);

  useEffect(() => {
    fetchInsiderTrades();
  }, [ticker]);

  const fetchStockHistory = async (selectedPeriod) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`http://localhost:3001/api/stock-history/${ticker}?period=${selectedPeriod}`);
      const data = await response.json();
      
      if (data.success) {
        setStockHistory(data);
      } else {
        setError(data.error || 'Failed to fetch stock data');
      }
    } catch (err) {
      setError('Failed to connect to server: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchInsiderTrades = async () => {
    setInsiderLoading(true);
    
    try {
      const response = await fetch(`http://localhost:3001/api/insider-trades/${ticker}`);
      const data = await response.json();
      
      if (data.success) {
        setInsiderTrades(data);
      }
    } catch (err) {
      console.error('Failed to fetch insider trades:', err);
    } finally {
      setInsiderLoading(false);
    }
  };



  const classifyInsiderRole = (title) => {
    if (!title) return 'Other';
    
    const titleUpper = title.toUpperCase();
    
    if (titleUpper.includes('CEO') || titleUpper.includes('CHIEF EXECUTIVE')) return 'CEO';
    if (titleUpper.includes('CFO') || titleUpper.includes('CHIEF FINANCIAL')) return 'CFO';
    if (titleUpper.includes('COO') || titleUpper.includes('CHIEF OPERATING')) return 'COO';
    if (titleUpper.includes('PRESIDENT') || titleUpper.includes('PRES')) return 'President';
    if (titleUpper.includes('CHAIRMAN') || titleUpper.includes('CHAIR')) return 'Chairman';
    if (titleUpper.includes('DIRECTOR') && !titleUpper.includes('CHIEF')) return 'Director';
    if (titleUpper.includes('10%') || titleUpper.includes('TEN PERCENT')) return '10% Owner';
    if (titleUpper.includes('OFFICER')) return 'Officer';
    
    return 'Other';
  };

  const mergedChartData = () => {
    if (!stockHistory || !stockHistory.history) return [];
    
    let data = [...stockHistory.history];
    
    // Collect all important dates (insider trades, backtest trades) that should be kept
    const importantDates = new Set();
    
    // Add insider trade dates
    if (insiderTrades?.purchases) {
      insiderTrades.purchases.forEach(trade => {
        const dateKey = trade.trade_date?.split('T')[0];
        if (dateKey) importantDates.add(dateKey);
      });
    }
    if (insiderTrades?.sales) {
      insiderTrades.sales.forEach(trade => {
        const dateKey = trade.trade_date?.split('T')[0];
        if (dateKey) importantDates.add(dateKey);
      });
    }
    
    // Add backtest trade dates (both entry and exit)
    if (backtestTrades) {
      backtestTrades.forEach(trade => {
        const entryDate = trade.entry_date?.split('T')[0];
        const exitDate = trade.exit_date?.split('T')[0];
        if (entryDate) importantDates.add(entryDate);
        if (exitDate) importantDates.add(exitDate);
      });
    }
    
    // Apply date-based filtering if focusDate is set
    if (focusDate) {
      const centerDate = new Date(focusDate + 'T12:00:00Z');
      const rangeInDays = {
        '1d': 0,
        '5d': 5,
        '1mo': 30,
        '3mo': 90,
        '6mo': 180,
        '1y': 365,
        '2y': 730,
        '5y': 1825,
        'max': null
      }[period];
      
      if (rangeInDays !== null && rangeInDays !== undefined) {
        if (period === '1d') {
          data = data.filter(point => {
            const dateStr = point.date.split('T')[0].split(' ')[0];
            const pointDate = new Date(dateStr + 'T12:00:00Z'); // Parse in UTC with midday to avoid timezone shifts
            const isSameDay = pointDate.getFullYear() === centerDate.getFullYear() &&
                              pointDate.getMonth() === centerDate.getMonth() &&
                              pointDate.getDate() === centerDate.getDate();
                return isSameDay;
          });
        } else {
          const halfRange = rangeInDays / 2;
          const startDate = new Date(centerDate);
          startDate.setDate(startDate.getDate() - halfRange);
          const endDate = new Date(centerDate);
          endDate.setDate(endDate.getDate() + halfRange);
          
          data = data.filter(point => {
            const dateStr = point.date.split('T')[0].split(' ')[0];
            const pointDate = new Date(dateStr + 'T12:00:00Z'); // Parse in UTC with midday to avoid timezone shifts
            const isInRange = pointDate >= startDate && pointDate <= endDate;
                return isInRange;
          });
        }
      }
    }
    
    // Create maps for insider purchases and sales by date
    const insiderPurchasesByDate = {};
    const insiderSalesByDate = {};
    
    // Helper function to find nearest trading day
    const findNearestTradingDay = (targetDateKey) => {
      const availableDates = data.map(point => point.date.split('T')[0].split(' ')[0]);
      
      // If the target date exists, use it
      if (availableDates.includes(targetDateKey)) {
        return targetDateKey;
      }
      
      // Otherwise, find the nearest date (prefer the next trading day after)
      const targetTime = new Date(targetDateKey).getTime();
      let nearestDate = null;
      let nearestDiff = Infinity;
      
      for (const dateKey of availableDates) {
        const dateTime = new Date(dateKey).getTime();
        const diff = Math.abs(dateTime - targetTime);
        
        // Prefer dates after the trade date (next trading day)
        if (dateTime >= targetTime) {
          if (diff < nearestDiff) {
            nearestDiff = diff;
            nearestDate = dateKey;
          }
        } else if (nearestDate === null || diff < nearestDiff) {
          // Only use date before if no date after found
          nearestDiff = diff;
          nearestDate = dateKey;
        }
      }
      
      return nearestDate;
    };
    
    if (insiderTrades) {
      insiderTrades.purchases?.forEach(trade => {
        const originalDateKey = trade.date.split('T')[0].split(' ')[0];
        const dateKey = findNearestTradingDay(originalDateKey);
        
        if (!dateKey) return; // Skip if no nearby trading day found
        
        if (!insiderPurchasesByDate[dateKey]) {
          insiderPurchasesByDate[dateKey] = { trades: [], totalValue: 0, count: 0 };
        }
        insiderPurchasesByDate[dateKey].trades.push({
          insider: trade.insider_name,
          title: trade.title,
          role: classifyInsiderRole(trade.title),
          shares: trade.shares,
          value: trade.value,
          originalDate: originalDateKey  // Always include the filing date
        });
        insiderPurchasesByDate[dateKey].totalValue += trade.value;
        insiderPurchasesByDate[dateKey].count += 1;
      });
      
      insiderTrades.sales?.forEach(trade => {
        const originalDateKey = trade.date.split('T')[0].split(' ')[0];
        const dateKey = findNearestTradingDay(originalDateKey);
        
        if (!dateKey) return; // Skip if no nearby trading day found
        
        if (!insiderSalesByDate[dateKey]) {
          insiderSalesByDate[dateKey] = { trades: [], totalValue: 0, count: 0 };
        }
        insiderSalesByDate[dateKey].trades.push({
          insider: trade.insider_name,
          title: trade.title,
          role: classifyInsiderRole(trade.title),
          shares: trade.shares,
          value: trade.value,
          originalDate: originalDateKey  // Always include the filing date
        });
        insiderSalesByDate[dateKey].totalValue += trade.value;
        insiderSalesByDate[dateKey].count += 1;
      });
    }
    
    // Create maps for backtest buy/sell signals by date
    const backtestBuysByDate = {};
    const backtestSellsByDate = {};
    
    if (backtestTrades) {
      backtestTrades.forEach(trade => {
        const entryDateKey = trade.entry_date?.split('T')[0];
        const exitDateKey = trade.exit_date?.split('T')[0];
        
        if (entryDateKey) {
          if (!backtestBuysByDate[entryDateKey]) {
            backtestBuysByDate[entryDateKey] = [];
          }
          backtestBuysByDate[entryDateKey].push({
            entry_price: parseFloat(trade.entry_price),
            position_size: parseFloat(trade.position_size),
            return_pct: parseFloat(trade.return_pct),
            profit_loss: parseFloat(trade.profit_loss),
            exit_reason: trade.exit_reason,
            exit_date: exitDateKey,
            insider_purchase_date: trade.insider_purchase_date
          });
        }
        
        if (exitDateKey) {
          if (!backtestSellsByDate[exitDateKey]) {
            backtestSellsByDate[exitDateKey] = [];
          }
          backtestSellsByDate[exitDateKey].push({
            exit_price: parseFloat(trade.exit_price),
            return_pct: parseFloat(trade.return_pct),
            profit_loss: parseFloat(trade.profit_loss),
            exit_reason: trade.exit_reason,
            entry_date: entryDateKey
          });
        }
      });
      
      // DEBUG: Log what dates have buy/sell signals
      if (ticker === 'GROV') {
        console.log('📍 Buy dates:', Object.keys(backtestBuysByDate));
        console.log('📍 Sell dates:', Object.keys(backtestSellsByDate));
      }
    }
    
    // Merge into chart data
    return data.map(point => {
      const dateKey = point.date.split('T')[0].split(' ')[0];
      
      const purchaseData = insiderPurchasesByDate[dateKey];
      const saleData = insiderSalesByDate[dateKey];
      const backtestBuys = backtestBuysByDate[dateKey] || [];
      const backtestSells = backtestSellsByDate[dateKey] || [];
      
      // Add trade line data - each trade gets its own line with 2 points
      // Use close price for visual alignment with stock curve
      const tradeLineData = {};
      if (backtestTrades) {
        backtestTrades.forEach((trade, idx) => {
          const entryDate = trade.entry_date?.split('T')[0];
          const exitDate = trade.exit_date?.split('T')[0];
          
          // Only add the price if this date is part of this trade line
          // Use close price for visual alignment
          if (dateKey === entryDate) {
            tradeLineData[`trade${idx}`] = point.close;
          } else if (dateKey === exitDate) {
            tradeLineData[`trade${idx}`] = point.close;
          } else {
            tradeLineData[`trade${idx}`] = null;
          }
        });
      }
      
      return {
        ...point,
        purchases: purchaseData?.totalValue || null,
        purchaseTrades: purchaseData?.trades || [],
        sales: saleData?.totalValue || null,
        saleTrades: saleData?.trades || [],
        // Create individual data keys for each backtest buy signal
        ...(backtestBuys.length > 0 ? backtestBuys.reduce((acc, buy, idx) => {
          acc[`backtestBuy${idx}`] = point.close;
          if (ticker === 'GROV') {
            console.log(`  ✅ Adding backtestBuy${idx} at ${dateKey}: ${point.close}`);
          }
          return acc;
        }, {}) : {}),
        backtestBuyData: backtestBuys,
        backtestSell: backtestSells.length > 0 ? point.close : null,
        backtestSellData: backtestSells,
        ...tradeLineData
      };
    });
  };

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload || payload.length === 0) return null;
    
    const data = payload[0].payload;
    const date = new Date(data.date);
    const formattedDate = date.toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' });
    
    return (
      <div className="bg-slate-800 border-2 border-slate-600 rounded-lg p-3 shadow-xl">
        <p className="text-white font-bold text-sm mb-2">
          {formattedDate}
        </p>
        <p className="text-slate-300 text-xs">
          Price: ${data.close?.toFixed(2)}
        </p>
        
        {data.purchaseTrades && data.purchaseTrades.length > 0 && (
          <div className="mt-2 pt-2 border-t border-slate-600">
            <p className="text-green-400 text-xs font-bold mb-1">
              🟢 Insider Purchases ({data.purchaseTrades.length})
            </p>
            {data.purchaseTrades.map((trade, idx) => {
              const formattedOriginalDate = trade.originalDate 
                ? new Date(trade.originalDate).toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' })
                : null;
              
              return (
                <div key={idx} className="text-xs text-slate-300 ml-2">
                  • {trade.insider} ({trade.role}): {formatAmount(trade.value)}
                  {formattedOriginalDate && (
                    <span className="text-slate-500 text-xxs ml-1">(filed {formattedOriginalDate})</span>
                  )}
                </div>
              );
            })}
          </div>
        )}
        
        {data.backtestBuyData && data.backtestBuyData.length > 0 && (
          <div className="mt-2 pt-2 border-t border-yellow-600">
            <p className="text-yellow-400 text-xs font-bold mb-1">
              📈 BACKTEST BUY SIGNAL ({data.backtestBuyData.length})
            </p>
            {data.backtestBuyData.map((trade, idx) => {
              const exitDate = trade.exit_date ? new Date(trade.exit_date).toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' }) : 'N/A';
              const insiderDate = trade.insider_purchase_date ? new Date(trade.insider_purchase_date).toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' }) : 'N/A';
              return (
                <div key={idx} className="text-xs text-yellow-200 ml-2">
                  • Entry: ${trade.entry_price?.toFixed(2)} | Invested: {formatAmount(trade.position_size)}
                  <br />
                  • Based on insider buy: {insiderDate}
                  <br />
                  • Till {exitDate} | Return: {trade.return_pct?.toFixed(1)}% | P/L: {formatAmount(trade.profit_loss)}
                </div>
              );
            })}
          </div>
        )}
        
        {data.backtestSellData && data.backtestSellData.length > 0 && (
          <div className="mt-2 pt-2 border-t border-cyan-600">
            <p className="text-cyan-400 text-xs font-bold mb-1">
              📉 BACKTEST SELL SIGNAL ({data.backtestSellData.length})
            </p>
            {data.backtestSellData.map((trade, idx) => {
              const entryDate = trade.entry_date ? new Date(trade.entry_date).toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' }) : 'N/A';
              return (
                <div key={idx} className="text-xs text-cyan-200 ml-2">
                  • Since {entryDate} | Exit: ${trade.exit_price?.toFixed(2)} | Return: {trade.return_pct?.toFixed(1)}%
                  <br />
                  • Reason: {trade.exit_reason} | P/L: ${trade.profit_loss?.toFixed(2)}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  const chartData = mergedChartData();
  const chartColor = stockHistory?.change_percent >= 0 ? '#10b981' : '#ef4444';

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-white text-xl font-bold">{ticker}</h3>
          {stockHistory && stockHistory.company_name && (
            <p className="text-slate-400 text-sm mt-1">{stockHistory.company_name}</p>
          )}
          {stockHistory && (
            <div className="mt-2 flex items-center gap-3">
              <span className="text-2xl font-bold text-white">
                ${stockHistory.current_price?.toFixed(2)}
              </span>
              <span className={`text-lg font-semibold ${stockHistory.change_percent >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {stockHistory.change_percent >= 0 ? '▲' : '▼'} {Math.abs(stockHistory.change_percent).toFixed(2)}%
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Period Selector */}
      <div className="mb-4">
        <div className="flex gap-2 flex-wrap items-center">
          {['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'].map((p) => (
            <button
              key={p}
              onClick={() => {
                setPeriod(p);
              }}
              disabled={loading}
              className={`px-3 py-1.5 text-sm rounded-lg transition-all ${
                period === p
                  ? 'bg-blue-600 text-white'
                  : loading
                  ? 'bg-slate-800/30 text-slate-600 cursor-not-allowed'
                  : 'bg-slate-700 text-slate-400 hover:bg-slate-600 hover:text-white'
              }`}
            >
              {p === 'max' ? 'MAX' : p.toUpperCase()}
            </button>
          ))}
          
          {/* Date Picker for Focus Date */}
          <div className="flex items-center gap-2 ml-2">
            <span className="text-slate-400 text-xs">Focus:</span>
            <input
              type="date"
              value={focusDate}
              onChange={(e) => setFocusDate(e.target.value)}
              min={stockHistory?.history?.[0]?.date.split('T')[0].split(' ')[0]}
              max={stockHistory?.history?.[stockHistory.history.length - 1]?.date.split('T')[0].split(' ')[0]}
              className="px-2 py-1 text-xs bg-slate-700 text-white rounded-lg border border-slate-600 focus:border-purple-500 focus:outline-none"
              placeholder="Today"
            />
            {focusDate && (
              <button
                onClick={() => setFocusDate('')}
                className="px-2 py-1 text-xs bg-red-600 hover:bg-red-500 text-white rounded-lg transition-all"
                title="Clear focus date"
              >
                ✕
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Insider Trades Summary */}
      {insiderTrades && (
        <div className="mb-4 flex gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-emerald-400">🟢 Purchases:</span>
            <span className="text-white font-semibold">{insiderTrades.total_purchases || 0}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-red-400">🔴 Sales:</span>
            <span className="text-white font-semibold">{insiderTrades.total_sales || 0}</span>
          </div>
        </div>
      )}

      {/* Backtest Legend */}
      {backtestTrades && backtestTrades.length > 0 && (() => {
        // Calculate statistics
        const totalInvested = backtestTrades.reduce((sum, trade) => sum + parseFloat(trade.position_size || 0), 0);
        const totalProfitLoss = backtestTrades.reduce((sum, trade) => sum + parseFloat(trade.profit_loss || 0), 0);
        const winRate = totalProfitLoss / totalInvested * 100;
        const isProfit = totalProfitLoss >= 0;
        
        return (
          <div className="mb-4 bg-slate-900 border border-yellow-600/30 rounded-lg p-3">
            <div className="flex items-start justify-between mb-2">
              <div className="text-yellow-400 font-semibold text-sm">📊 Backtest Signals ({backtestTrades.length} trades)</div>
              <div className="text-right">
                <div className="text-xs text-slate-400">Total Invested: <span className="text-white font-semibold">${totalInvested.toLocaleString('en-US', {maximumFractionDigits: 0})}</span></div>
                <div className="text-xs text-slate-400">
                  Net {isProfit ? 'Profit' : 'Loss'}: 
                  <span className={`font-semibold ml-1 ${isProfit ? 'text-emerald-400' : 'text-red-400'}`}>
                    ${Math.abs(totalProfitLoss).toLocaleString('en-US', {maximumFractionDigits: 0})} ({isProfit ? '+' : '-'}{Math.abs(winRate).toFixed(1)}%)
                  </span>
                </div>
              </div>
            </div>
            <div className="flex gap-4 text-xs flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-yellow-400">★</span>
                <span className="text-slate-300">Buy Entry</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-block w-3 h-3 bg-emerald-500 border-2 border-white"></span>
                <span className="text-slate-300">Sell Exit (Profit)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-block w-3 h-3 bg-red-500 border-2 border-white"></span>
                <span className="text-slate-300">Sell Exit (Loss)</span>
              </div>
            </div>
          </div>
        );
      })()}

      {/* Chart */}
      <div className="bg-slate-900 rounded-lg p-3">
        {loading ? (
          <div className="h-64 flex items-center justify-center text-slate-400">
            Loading chart data...
          </div>
        ) : error ? (
          <div className="h-64 flex items-center justify-center text-red-400">
            Error: {error}
          </div>
        ) : chartData.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-slate-400">
            No data available
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={`colorPrice-${ticker}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={chartColor} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={chartColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis 
                dataKey="date" 
                stroke="#94a3b8"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                tickFormatter={(value) => {
                  const date = new Date(value);
                  if (period === '1d' && value.includes(':')) {
                    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
                  }
                  if (period === '5d' || period === '1mo') {
                    return `${date.getDate()} ${date.toLocaleString('en-US', { month: 'short' })}`;
                  }
                  if (period === '3mo' || period === '6mo') {
                    return date.toLocaleString('en-US', { month: 'short', year: 'numeric' });
                  }
                  if (period === '1y') {
                    if (focusDate) {
                      return date.toLocaleString('en-US', { month: 'short', year: '2-digit' });
                    }
                    return date.getFullYear().toString();
                  }
                  return date.getFullYear().toString();
                }}
              />
              <YAxis 
                yAxisId="price"
                stroke="#94a3b8"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                domain={['auto', 'auto']}
                tickFormatter={(value) => `$${value.toFixed(2)}`}
              />
              <YAxis 
                yAxisId="insider"
                orientation="right"
                stroke="#94a3b8"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                tickFormatter={(value) => {
                  if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
                  if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
                  return `$${value}`;
                }}
              />
              <ChartTooltip 
                content={<CustomTooltip />} 
                cursor={{ stroke: '#475569', strokeWidth: 1, strokeDasharray: '3 3' }}
              />
              <Area 
                yAxisId="price"
                type="monotone" 
                dataKey="close" 
                stroke={chartColor} 
                strokeWidth={2}
                fillOpacity={1} 
                fill={`url(#colorPrice-${ticker})`}
                activeDot={false}
                isAnimationActive={false}
              />
              
              {/* Backtest trade lines - buy dots, sell dots, connecting lines */}
              {backtestTrades && backtestTrades.length > 0 && (
                <>
                  {/* Connecting lines for each trade */}
                  {backtestTrades.map((trade, idx) => {
                    const isProfitable = parseFloat(trade.profit_loss) > 0;
                    const lineColor = isProfitable ? '#10b981' : '#ef4444';
                    
                    return (
                      <Line
                        key={`trade-line-${idx}`}
                        yAxisId="price"
                        type="linear"
                        dataKey={`trade${idx}`}
                        stroke={lineColor}
                        strokeWidth={4}
                        connectNulls={true}
                        dot={false}
                        activeDot={false}
                        isAnimationActive={false}
                      />
                    );
                  })}
                  
                  {/* Buy dots (yellow circles) - render on top */}
                  {/* Create separate scatter for each backtest buy signal to show multiple on same date */}
                  {backtestTrades && backtestTrades.map((trade, idx) => (
                    <Scatter
                      key={`backtest-buy-${idx}`}
                      yAxisId="price"
                      dataKey={`backtestBuy${idx}`}
                      fill="#fbbf24"
                      isAnimationActive={false}
                      shape={(props) => {
                        const { cx, cy, payload } = props;
                        const dataKey = `backtestBuy${idx}`;
                        
                        if (ticker === 'GROV') {
                          console.log(`🔴 Buy marker shape called for ${dataKey}:`, {
                            cx, cy, 
                            hasPayload: !!payload,
                            hasDataKey: payload?.[dataKey] !== undefined,
                            value: payload?.[dataKey]
                          });
                        }
                        
                        if (!payload || !payload[dataKey]) return null;
                        
                        return (
                          <circle
                            cx={cx}
                            cy={cy}
                            r={8}
                            fill="#fbbf24"
                            stroke="#fff"
                            strokeWidth={2}
                          />
                        );
                      }}
                    />
                  ))}
                  
                  {/* Sell dots (colored squares) - render on top */}
                  <Scatter
                    yAxisId="price"
                    dataKey="backtestSell"
                    isAnimationActive={false}
                    shape={(props) => {
                      const { cx, cy, payload } = props;
                      
                      if (ticker === 'GROV') {
                        console.log(`🟢 Sell marker shape called:`, {
                          cx, cy,
                          hasPayload: !!payload,
                          hasDataKey: payload?.backtestSell !== undefined,
                          value: payload?.backtestSell
                        });
                      }
                      
                      if (!payload || !payload.backtestSell) return null;
                      
                      // Determine color based on profit/loss from the sell data
                      const sellData = payload.backtestSellData?.[0];
                      const isProfitable = sellData && parseFloat(sellData.profit_loss) > 0;
                      const color = isProfitable ? '#10b981' : '#ef4444';
                      
                      return (
                        <rect
                          x={cx - 6}
                          y={cy - 6}
                          width={12}
                          height={12}
                          fill={color}
                          stroke="#fff"
                          strokeWidth={2}
                        />
                      );
                    }}
                  />
                </>
              )}
              
              {insiderTrades && insiderTrades.total_purchases > 0 && (
                <Scatter
                  yAxisId="insider"
                  dataKey="purchases"
                  fill="#10b981"
                  isAnimationActive={false}
                  shape={(props) => {
                    const { cx, cy, payload, yAxis } = props;
                    if (!payload || !payload.purchases || payload.purchases <= 0) return null;
                    
                    // Get the chart bottom from yAxis range
                    const chartBottom = yAxis?.range?.[0] || 290; // yAxis.range[0] is the bottom pixel coordinate
                    
                    return (
                      <g key={`purchase-${cx}-${cy}`}>
                        {/* Vertical dotted line from bottom to dot */}
                        <line
                          x1={cx}
                          y1={chartBottom}
                          x2={cx}
                          y2={cy}
                          stroke="#10b981"
                          strokeWidth={3}
                          strokeDasharray="4 4"
                          strokeOpacity={0.6}
                        />
                        {/* Circle at the top */}
                        <circle
                          cx={cx}
                          cy={cy}
                          r={8}
                          fill="#10b981"
                          stroke="#fff"
                          strokeWidth={2}
                        />
                      </g>
                    );
                  }}
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

export default AllChartsView;
