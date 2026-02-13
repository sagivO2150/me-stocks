import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as ChartTooltip, ResponsiveContainer, Area, AreaChart, ComposedChart, Scatter } from 'recharts';

const AllChartsView = ({ stocks }) => {
  return (
    <div className="grid grid-cols-1 gap-8">
      {stocks.map((stock) => (
        <SingleStockChart key={stock.ticker} ticker={stock.ticker} />
      ))}
    </div>
  );
};

const SingleStockChart = ({ ticker }) => {
  const [stockHistory, setStockHistory] = useState(null);
  const [insiderTrades, setInsiderTrades] = useState(null);
  const [loading, setLoading] = useState(true);
  const [insiderLoading, setInsiderLoading] = useState(true);
  const [error, setError] = useState(null);
  const [period, setPeriod] = useState('1y'); // Default to 1 year
  const [focusDate, setFocusDate] = useState(''); // Empty by default

  useEffect(() => {
    if (focusDate) {
      if (!stockHistory?.history) {
        fetchStockHistory('max');
        return;
      }
      
      const firstAvailableDate = new Date(stockHistory.history[0].date.split('T')[0].split(' ')[0]);
      const lastAvailableDate = new Date(stockHistory.history[stockHistory.history.length - 1].date.split('T')[0].split(' ')[0]);
      const targetDate = new Date(focusDate + 'T00:00:00');
      
      if (targetDate < firstAvailableDate || targetDate > lastAvailableDate) {
        fetchStockHistory('max');
        return;
      }
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
    
    // Apply date-based filtering if focusDate is set
    if (focusDate) {
      const centerDate = new Date(focusDate + 'T00:00:00');
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
            const pointDate = new Date(dateStr + 'T00:00:00');
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
            const pointDate = new Date(dateStr + 'T00:00:00');
            const isInRange = pointDate >= startDate && pointDate <= endDate;
            return isInRange;
          });
        }
      }
    }
    
    // Create maps for insider purchases and sales by date
    const insiderPurchasesByDate = {};
    const insiderSalesByDate = {};
    
    if (insiderTrades) {
      insiderTrades.purchases?.forEach(trade => {
        const dateKey = trade.date.split('T')[0].split(' ')[0];
        if (!insiderPurchasesByDate[dateKey]) {
          insiderPurchasesByDate[dateKey] = { trades: [], totalValue: 0, count: 0 };
        }
        insiderPurchasesByDate[dateKey].trades.push({
          insider: trade.insider_name,
          title: trade.title,
          role: classifyInsiderRole(trade.title),
          shares: trade.shares,
          value: trade.value
        });
        insiderPurchasesByDate[dateKey].totalValue += trade.value;
        insiderPurchasesByDate[dateKey].count += 1;
      });
      
      insiderTrades.sales?.forEach(trade => {
        const dateKey = trade.date.split('T')[0].split(' ')[0];
        if (!insiderSalesByDate[dateKey]) {
          insiderSalesByDate[dateKey] = { trades: [], totalValue: 0, count: 0 };
        }
        insiderSalesByDate[dateKey].trades.push({
          insider: trade.insider_name,
          title: trade.title,
          role: classifyInsiderRole(trade.title),
          shares: trade.shares,
          value: trade.value
        });
        insiderSalesByDate[dateKey].totalValue += trade.value;
        insiderSalesByDate[dateKey].count += 1;
      });
    }
    
    // Merge into chart data
    return data.map(point => {
      const dateKey = point.date.split('T')[0].split(' ')[0];
      
      const purchaseData = insiderPurchasesByDate[dateKey];
      const saleData = insiderSalesByDate[dateKey];
      
      return {
        ...point,
        purchases: purchaseData?.totalValue || null,
        purchaseTrades: purchaseData?.trades || [],
        sales: saleData?.totalValue || null,
        saleTrades: saleData?.trades || []
      };
    });
  };

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload || payload.length === 0) return null;
    
    const data = payload[0].payload;
    const date = new Date(data.date);
    
    return (
      <div className="bg-slate-800 border-2 border-slate-600 rounded-lg p-3 shadow-xl">
        <p className="text-white font-bold text-sm mb-2">
          {date.toLocaleDateString('en-US', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' })}
        </p>
        <p className="text-emerald-400 text-sm">
          Close: <span className="font-bold">${data.close?.toFixed(2)}</span>
        </p>
        
        {data.purchaseTrades && data.purchaseTrades.length > 0 && (
          <div className="mt-2 pt-2 border-t border-slate-600">
            <p className="text-green-400 text-xs font-bold mb-1">
              🟢 Insider Purchases ({data.purchaseTrades.length})
            </p>
            {data.purchaseTrades.map((trade, idx) => (
              <div key={idx} className="text-xs text-slate-300 ml-2">
                • {trade.insider} ({trade.role}): ${(trade.value / 1000).toFixed(0)}K
              </div>
            ))}
          </div>
        )}
        
        {data.saleTrades && data.saleTrades.length > 0 && (
          <div className="mt-2 pt-2 border-t border-slate-600">
            <p className="text-red-400 text-xs font-bold mb-1">
              🔴 Insider Sales ({data.saleTrades.length})
            </p>
            {data.saleTrades.map((trade, idx) => (
              <div key={idx} className="text-xs text-slate-300 ml-2">
                • {trade.insider} ({trade.role}): ${(trade.value / 1000).toFixed(0)}K
              </div>
            ))}
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
              onClick={() => setPeriod(p)}
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
              {insiderTrades && insiderTrades.total_purchases > 0 && (
                <Line
                  yAxisId="insider"
                  type="monotone"
                  dataKey="purchases"
                  stroke="#10b981"
                  strokeWidth={2}
                  isAnimationActive={false}
                  strokeDasharray="3 3"
                  dot={(dotProps) => {
                    const { cx, cy, payload } = dotProps;
                    if (!payload || !payload.purchaseTrades || payload.purchaseTrades.length === 0) {
                      return <circle key={`purchase-empty-${cx}-${cy}`} cx={cx} cy={cy} r={0} fill="none" />;
                    }
                    
                    const trades = payload.purchaseTrades;
                    const numTrades = trades.length;
                    
                    if (numTrades === 1) {
                      return (
                        <circle 
                          key={`purchase-${cx}-${cy}`} 
                          cx={cx} 
                          cy={cy} 
                          r={6} 
                          fill="#10b981" 
                          stroke="#fff" 
                          strokeWidth={2}
                        />
                      );
                    } else {
                      const spacing = 3;
                      const startX = cx - ((numTrades - 1) * spacing) / 2;
                      return (
                        <g key={`purchase-group-${cx}-${cy}`}>
                          {trades.map((trade, idx) => (
                            <circle
                              key={`purchase-${cx}-${cy}-${idx}`}
                              cx={startX + (idx * spacing)}
                              cy={cy}
                              r={5}
                              fill="#10b981"
                              stroke="#fff"
                              strokeWidth={1.5}
                            />
                          ))}
                        </g>
                      );
                    }
                  }}
                />
              )}
              {insiderTrades && insiderTrades.total_sales > 0 && (
                <Line
                  yAxisId="insider"
                  type="monotone"
                  dataKey="sales"
                  stroke="#ef4444"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  isAnimationActive={false}
                  dot={(dotProps) => {
                    const { cx, cy, payload } = dotProps;
                    if (!payload || !payload.saleTrades || payload.saleTrades.length === 0) {
                      return <circle key={`sale-empty-${cx}-${cy}`} cx={cx} cy={cy} r={0} fill="none" />;
                    }
                    
                    const trades = payload.saleTrades;
                    const numTrades = trades.length;
                    
                    if (numTrades === 1) {
                      return <circle key={`sale-${cx}-${cy}`} cx={cx} cy={cy} r={6} fill="#ef4444" stroke="#fff" strokeWidth={2} />;
                    } else {
                      const spacing = 3;
                      const startX = cx - ((numTrades - 1) * spacing) / 2;
                      return (
                        <g key={`sale-group-${cx}-${cy}`}>
                          {trades.map((trade, idx) => (
                            <circle
                              key={`sale-${cx}-${cy}-${idx}`}
                              cx={startX + (idx * spacing)}
                              cy={cy}
                              r={5}
                              fill="#ef4444"
                              stroke="#fff"
                              strokeWidth={1.5}
                            />
                          ))}
                        </g>
                      );
                    }
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
