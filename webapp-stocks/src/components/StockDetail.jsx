import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as ChartTooltip, ResponsiveContainer, Area, AreaChart, ComposedChart } from 'recharts';
import Tooltip from './Tooltip';

const StockDetail = ({ trade, onClose }) => {
  const [stockHistory, setStockHistory] = useState(null);
  const [insiderTrades, setInsiderTrades] = useState(null);
  const [loading, setLoading] = useState(true);
  const [insiderLoading, setInsiderLoading] = useState(true);
  const [error, setError] = useState(null);
  const [period, setPeriod] = useState('1y');

  const ticker = trade.Ticker;

  useEffect(() => {
    fetchStockHistory(period);
  }, [period, ticker]);

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

  // Parse trade data (same as TradeCard)
  const insidersCount = parseInt(trade.Insiders) || 0;
  const cobCount = parseInt(trade.COB_Count) || 0;
  const ceoCount = parseInt(trade.CEO_Count) || 0;
  const presCount = parseInt(trade.Pres_Count) || 0;
  const cfoCount = parseInt(trade.CFO_Count) || 0;
  const cooCount = parseInt(trade.COO_Count) || 0;
  const gcCount = parseInt(trade.GC_Count) || 0;
  const vpCount = parseInt(trade.VP_Count) || 0;
  const directorCount = parseInt(trade.Director_Count) || 0;
  const ownerCount = parseInt(trade.Owner_Count) || 0;
  const otherCount = parseInt(trade.Other_Count) || 0;
  const value = trade.Value;
  const tradeDate = trade.Trade_Date;
  const deltaOwn = trade.Delta_Own;
  const skinInGame = trade.Skin_in_Game;
  const rainyDayScore = parseInt(trade.Rainy_Day_Score) || 0;
  const healthFlags = trade.Health_Flags;
  const targetMeanPrice = parseFloat(trade.Target_Mean_Price);
  const currentPrice = parseFloat(trade.Current_Price);
  const sector = trade.Sector;
  const sectorType = trade.Sector_Type;
  const scoreReasons = trade.Score_Reasons;

  // Build role breakdown
  const roleBreakdown = [];
  if (cobCount > 0) roleBreakdown.push(cobCount === 1 ? 'COB' : `${cobCount} COBs`);
  if (ceoCount > 0) roleBreakdown.push(ceoCount === 1 ? 'CEO' : `${ceoCount} CEOs`);
  if (presCount > 0) roleBreakdown.push(presCount === 1 ? 'Pres' : `${presCount} Pres`);
  if (cfoCount > 0) roleBreakdown.push(cfoCount === 1 ? 'CFO' : `${cfoCount} CFOs`);
  if (cooCount > 0) roleBreakdown.push(cooCount === 1 ? 'COO' : `${cooCount} COOs`);
  if (gcCount > 0) roleBreakdown.push(gcCount === 1 ? 'GC' : `${gcCount} GCs`);
  if (vpCount > 0) roleBreakdown.push(`${vpCount} VP${vpCount > 1 ? 's' : ''}`);
  if (directorCount > 0) roleBreakdown.push(`${directorCount} Director${directorCount > 1 ? 's' : ''}`);
  if (ownerCount > 0) roleBreakdown.push(`${ownerCount} Owner${ownerCount > 1 ? 's' : ''}`);
  if (otherCount > 0) roleBreakdown.push(`${otherCount} Other`);
  const roleBreakdownText = roleBreakdown.join(', ');

  // Calculate upside
  let upside = 'N/A';
  if (targetMeanPrice && currentPrice && !isNaN(targetMeanPrice) && !isNaN(currentPrice)) {
    const discountPct = ((targetMeanPrice - currentPrice) / currentPrice) * 100;
    upside = discountPct > 0 ? `+${discountPct.toFixed(1)}%` : `${discountPct.toFixed(1)}%`;
  }

  const getScoreColor = (score) => {
    if (score >= 8) return 'text-emerald-400 border-emerald-400';
    if (score >= 6) return 'text-blue-400 border-blue-400';
    if (score >= 4) return 'text-yellow-400 border-yellow-400';
    return 'text-orange-400 border-orange-400';
  };

  const getScoreBg = (score) => {
    if (score >= 8) return 'bg-emerald-500/20';
    if (score >= 6) return 'bg-blue-500/20';
    if (score >= 4) return 'bg-yellow-500/20';
    return 'bg-orange-500/20';
  };

  // Merge insider trades with stock history for chart display
  const mergedChartData = () => {
    if (!stockHistory || !stockHistory.history) return [];
    
    const data = [...stockHistory.history];
    
    if (!insiderTrades) return data;
    
    // Create maps for purchases and sales by date (just date, not time)
    const purchasesByDate = {};
    const salesByDate = {};
    
    insiderTrades.purchases?.forEach(trade => {
      const dateKey = trade.date; // Already in YYYY-MM-DD format
      if (!purchasesByDate[dateKey]) {
        purchasesByDate[dateKey] = { shares: 0, value: 0, count: 0 };
      }
      purchasesByDate[dateKey].shares += trade.shares;
      purchasesByDate[dateKey].value += trade.value;
      purchasesByDate[dateKey].count += 1;
    });
    
    insiderTrades.sales?.forEach(trade => {
      const dateKey = trade.date;
      if (!salesByDate[dateKey]) {
        salesByDate[dateKey] = { shares: 0, value: 0, count: 0 };
      }
      salesByDate[dateKey].shares += trade.shares;
      salesByDate[dateKey].value += trade.value;
      salesByDate[dateKey].count += 1;
    });
    
    // Merge with stock data
    return data.map(point => {
      const dateKey = point.date.split(' ')[0]; // Extract date part (YYYY-MM-DD)
      
      return {
        ...point,
        purchases: purchasesByDate[dateKey]?.value || 0,
        sales: salesByDate[dateKey]?.value || 0,
        purchaseShares: purchasesByDate[dateKey]?.shares || 0,
        saleShares: salesByDate[dateKey]?.shares || 0,
        purchaseCount: purchasesByDate[dateKey]?.count || 0,
        saleCount: salesByDate[dateKey]?.count || 0
      };
    });
  };

  // Custom tooltip for chart - only show when hovering over insider trades
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      
      // Only show tooltip if there's insider activity on this date
      if (data.purchaseCount === 0 && data.saleCount === 0) {
        return null;
      }
      
      return (
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-xl">
          <p className="text-slate-300 text-sm font-semibold mb-2">{data.date}</p>
          <p className="text-slate-400 text-xs mb-2">Stock Price: ${data.close?.toFixed(2) || payload[0].value.toFixed(2)}</p>
          {data.purchaseCount > 0 && (
            <div className="mt-2 pt-2 border-t border-slate-700">
              <p className="text-emerald-400 text-sm font-semibold">
                🟢 {data.purchaseCount} Insider Purchase{data.purchaseCount > 1 ? 's' : ''}
              </p>
              <p className="text-emerald-400 text-xs">
                {data.purchaseShares.toLocaleString()} shares • ${
                  data.purchases >= 1000000 
                    ? (data.purchases / 1000000).toFixed(2) + 'M'
                    : data.purchases >= 1000
                    ? (data.purchases / 1000).toFixed(1) + 'K'
                    : data.purchases.toFixed(0)
                }
              </p>
            </div>
          )}
          {data.saleCount > 0 && (
            <div className="mt-2 pt-2 border-t border-slate-700">
              <p className="text-red-400 text-sm font-semibold">
                🔴 {data.saleCount} Insider Sale{data.saleCount > 1 ? 's' : ''}
              </p>
              <p className="text-red-400 text-xs">
                {data.saleShares.toLocaleString()} shares • ${
                  data.sales >= 1000000 
                    ? (data.sales / 1000000).toFixed(2) + 'M'
                    : data.sales >= 1000
                    ? (data.sales / 1000).toFixed(1) + 'K'
                    : data.sales.toFixed(0)
                }
              </p>
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  // Determine if price is up or down
  const isPriceUp = stockHistory && stockHistory.change_24h_pct > 0;
  const chartColor = isPriceUp ? '#34d399' : '#f87171';

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-6xl w-full max-h-[90vh] overflow-y-auto shadow-2xl focus:outline-none focus:border-slate-700 active:outline-none active:border-slate-700" style={{outline: 'none'}}>
        {/* Header */}
        <div className="sticky top-0 bg-slate-900 border-b border-slate-700 p-6 flex justify-between items-start z-10">
          <div className="flex-1">
            <div className="flex items-center gap-4">
              <h2 className="text-4xl font-bold text-white">{ticker}</h2>
              {stockHistory && (
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold text-white">${stockHistory.current_price}</span>
                  <span className={`text-lg font-semibold ${isPriceUp ? 'text-emerald-400' : 'text-red-400'}`}>
                    {isPriceUp ? '↑' : '↓'} {Math.abs(stockHistory.change_24h_pct).toFixed(2)}%
                  </span>
                </div>
              )}
            </div>
            <p className="text-slate-400 text-lg mt-2">{sector || 'Unknown Sector'}</p>
            {stockHistory && stockHistory.company_name && (
              <p className="text-slate-500 text-sm mt-1">{stockHistory.company_name}</p>
            )}
          </div>
          
          {/* Score Circle */}
          <div className="flex items-center gap-4">
            <Tooltip text="Overall conviction score (0-10). Based on: insider clustering (3+ = good), high transaction value, ownership increase %, financial health, and sector defensive strength.">
              <div className={`flex flex-col items-center justify-center w-24 h-24 rounded-full border-4 ${getScoreColor(rainyDayScore)} ${getScoreBg(rainyDayScore)}`}>
                <div className={`text-3xl font-bold ${getScoreColor(rainyDayScore)}`}>
                  {rainyDayScore}
                </div>
                <div className="text-xs text-slate-400">/ 10</div>
              </div>
            </Tooltip>
            
            <button 
              onClick={onClose}
              className="text-slate-400 hover:text-white transition-colors text-3xl leading-none p-2"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Period Selector */}
          <div className="mb-6 flex gap-2">
            {['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y'].map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-4 py-2 rounded-lg transition-all ${
                  period === p
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white'
                }`}
              >
                {p.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Chart */}
          <div className="bg-slate-800/50 rounded-xl p-6 mb-6" style={{outline: 'none'}} tabIndex={-1}>
            {/* Insider Activity Legend */}
            {insiderTrades && (insiderTrades.total_purchases > 0 || insiderTrades.total_sales > 0) && (
              <div className="flex justify-center gap-6 mb-4 text-sm">
                {insiderTrades.total_purchases > 0 && (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-0.5 bg-emerald-400"></div>
                    <span className="text-slate-300">
                      Insider Purchases ({insiderTrades.total_purchases})
                    </span>
                  </div>
                )}
                {insiderTrades.total_sales > 0 && (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-0.5 bg-red-500" style={{backgroundImage: 'repeating-linear-gradient(90deg, #ef4444 0, #ef4444 3px, transparent 3px, transparent 6px)'}}></div>
                    <span className="text-slate-300">
                      Insider Sales ({insiderTrades.total_sales})
                    </span>
                  </div>
                )}
              </div>
            )}

            {loading && (
              <div className="h-96 flex items-center justify-center">
                <div className="text-slate-400 text-xl">Loading chart...</div>
              </div>
            )}
            
            {error && (
              <div className="h-96 flex items-center justify-center">
                <div className="text-red-400 text-xl">Error: {error}</div>
              </div>
            )}
            
            {!loading && !error && stockHistory && stockHistory.history && (
              <ResponsiveContainer width="100%" height={400}>
                <ComposedChart data={mergedChartData()} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={chartColor} stopOpacity={0.3}/>
                      <stop offset="95%" stopColor={chartColor} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis 
                    dataKey="date" 
                    stroke="#94a3b8"
                    tick={{ fill: '#94a3b8' }}
                    tickFormatter={(value) => {
                      const date = new Date(value);
                      // For intraday data (includes time), show time
                      if (value.includes(':')) {
                        const hours = date.getHours();
                        const minutes = date.getMinutes();
                        const ampm = hours >= 12 ? 'PM' : 'AM';
                        const displayHours = hours % 12 || 12;
                        return `${displayHours}:${minutes.toString().padStart(2, '0')} ${ampm}`;
                      }
                      // For daily data, show month/day
                      return `${date.getMonth() + 1}/${date.getDate()}`;
                    }}
                  />
                  <YAxis 
                    yAxisId="price"
                    stroke="#94a3b8"
                    tick={{ fill: '#94a3b8' }}
                    domain={['auto', 'auto']}
                    tickFormatter={(value) => `$${value.toFixed(2)}`}
                  />
                  <YAxis 
                    yAxisId="insider"
                    orientation="right"
                    stroke="#94a3b8"
                    tick={{ fill: '#94a3b8' }}
                    tickFormatter={(value) => {
                      if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
                      if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
                      return `$${value}`;
                    }}
                  />
                  <ChartTooltip content={<CustomTooltip />} />
                  <Area 
                    yAxisId="price"
                    type="monotone" 
                    dataKey="close" 
                    stroke={chartColor} 
                    strokeWidth={2}
                    fillOpacity={1} 
                    fill="url(#colorPrice)"
                    activeDot={false}
                    isAnimationActive={false}
                  />
                  {insiderTrades && insiderTrades.total_purchases > 0 && (
                    <Line 
                      yAxisId="insider"
                      type="monotone"
                      dataKey="purchases"
                      stroke="#10b981"
                      strokeWidth={3}
                      dot={(dotProps) => {
                        const { cx, cy, payload } = dotProps;
                        if (payload && payload.purchases > 0) {
                          return <circle key={`purchase-${cx}-${cy}`} cx={cx} cy={cy} r={5} fill="#10b981" stroke="#fff" strokeWidth={2} />;
                        }
                        // Return invisible dot to maintain line continuity
                        return <circle key={`purchase-empty-${cx}-${cy}`} cx={cx} cy={cy} r={0} fill="none" />;
                      }}
                      activeDot={(dotProps) => {
                        const { cx, cy, payload } = dotProps;
                        if (payload && payload.purchases > 0) {
                          return <circle key={`purchase-active-${cx}-${cy}`} cx={cx} cy={cy} r={8} fill="#10b981" stroke="#fff" strokeWidth={3} />;
                        }
                        return false;
                      }}
                    />
                  )}
                  {insiderTrades && insiderTrades.total_sales > 0 && (
                    <Line 
                      yAxisId="insider"
                      type="monotone"
                      dataKey="sales"
                      stroke="#ef4444"
                      strokeWidth={3}
                      strokeDasharray="5 5"
                      dot={(dotProps) => {
                        const { cx, cy, payload } = dotProps;
                        if (payload && payload.sales > 0) {
                          return <circle key={`sale-${cx}-${cy}`} cx={cx} cy={cy} r={5} fill="#ef4444" stroke="#fff" strokeWidth={2} />;
                        }
                        // Return invisible dot to maintain line continuity
                        return <circle key={`sale-empty-${cx}-${cy}`} cx={cx} cy={cy} r={0} fill="none" />;
                      }}
                      activeDot={(dotProps) => {
                        const { cx, cy, payload } = dotProps;
                        if (payload && payload.sales > 0) {
                          return <circle key={`sale-active-${cx}-${cy}`} cx={cx} cy={cy} r={8} fill="#ef4444" stroke="#fff" strokeWidth={3} />;
                        }
                        return false;
                      }}
                    />
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Two Column Layout for Details */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Column: Insider Trade Info */}
            <div className="space-y-4">
              <h3 className="text-xl font-bold text-white mb-4">Insider Trade Details</h3>
              
              {/* Badges */}
              <div className="flex flex-wrap gap-2">
                <Tooltip text={`Number of insiders buying this stock. Breakdown: ${roleBreakdownText}. CEO/CFO/COO buys = C-suite conviction (strongest signal).`}>
                  <span className="px-3 py-2 bg-blue-500/20 text-blue-400 rounded-lg text-sm font-medium border border-blue-500/30">
                    👥 {insidersCount} Insiders ({roleBreakdownText})
                  </span>
                </Tooltip>

                {skinInGame === 'YES' && (
                  <Tooltip text="HIGH CONVICTION = Insiders increased their ownership by 10%+ OR bought $500k+.">
                    <span className="px-3 py-2 bg-emerald-500/20 text-emerald-400 rounded-lg text-sm font-medium border border-emerald-500/30">
                      💎 HIGH CONVICTION
                    </span>
                  </Tooltip>
                )}
              </div>

              {/* Trade Stats */}
              <div className="bg-slate-800/50 rounded-xl p-4 space-y-3">
                <div className="flex justify-between items-center">
                  <Tooltip text="Total dollar amount insiders spent buying shares. Higher = more serious.">
                    <span className="text-slate-400 border-b border-dotted border-slate-600 cursor-help">Trade Value</span>
                  </Tooltip>
                  <span className="text-white font-semibold text-lg">{value}</span>
                </div>
                
                <div className="flex justify-between items-center">
                  <Tooltip text="How much their personal stake increased. +10% = significant commitment.">
                    <span className="text-slate-400 border-b border-dotted border-slate-600 cursor-help">Ownership Change</span>
                  </Tooltip>
                  <span className="text-emerald-400 font-semibold text-lg">{deltaOwn}</span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Trade Date</span>
                  <span className="text-white font-semibold">{tradeDate}</span>
                </div>

                {upside !== 'N/A' && (
                  <div className="flex justify-between items-center pt-3 border-t border-slate-700">
                    <Tooltip text="Gap between current price and Wall Street analyst average target.">
                      <span className="text-slate-400 border-b border-dotted border-slate-600 cursor-help">Upside to Target</span>
                    </Tooltip>
                    <span className={`font-bold text-2xl ${upside.startsWith('+') ? 'text-emerald-400' : 'text-red-400'}`}>
                      {upside}
                    </span>
                  </div>
                )}
              </div>

              {/* Health Flags */}
              {healthFlags && healthFlags !== 'N/A' && (
                <div className="bg-slate-800/50 rounded-xl p-4">
                  <Tooltip text="Financial health indicators from company fundamentals.">
                    <div className="text-sm text-slate-400 mb-2 border-b border-dotted border-slate-600 inline-block cursor-help">Financial Health</div>
                  </Tooltip>
                  <div className="text-slate-200">{healthFlags}</div>
                </div>
              )}

              {/* Sector Type */}
              {sectorType && (
                <div>
                  {sectorType.includes('DEFENSIVE') && (
                    <Tooltip text="DEFENSIVE sectors = Safe havens during market downturns.">
                      <div className="bg-green-500/10 border border-green-500/30 rounded-lg px-4 py-3">
                        <div className="text-green-400 font-semibold">🛡️ {sectorType}</div>
                      </div>
                    </Tooltip>
                  )}
                  {sectorType.includes('AGGRESSIVE') && (
                    <Tooltip text="AGGRESSIVE sectors = High risk/high reward.">
                      <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3">
                        <div className="text-red-400 font-semibold">⚠️ {sectorType}</div>
                      </div>
                    </Tooltip>
                  )}
                  {sectorType.includes('NEUTRAL') && (
                    <Tooltip text="NEUTRAL sectors = Balanced risk/reward.">
                      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg px-4 py-3">
                        <div className="text-blue-400 font-semibold">⚖️ {sectorType}</div>
                      </div>
                    </Tooltip>
                  )}
                </div>
              )}
            </div>

            {/* Right Column: Stock Fundamentals */}
            <div className="space-y-4">
              <h3 className="text-xl font-bold text-white mb-4">Stock Fundamentals</h3>
              
              {stockHistory && (
                <div className="bg-slate-800/50 rounded-xl p-4 space-y-3">
                  {stockHistory.market_cap && stockHistory.market_cap !== 'N/A' && (
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Market Cap</span>
                      <span className="text-white font-semibold">
                        ${(stockHistory.market_cap / 1000000000).toFixed(2)}B
                      </span>
                    </div>
                  )}
                  
                  {stockHistory.pe_ratio && stockHistory.pe_ratio !== 'N/A' && (
                    <div className="flex justify-between items-center">
                      <Tooltip text="Price-to-Earnings ratio. Lower values may indicate undervaluation.">
                        <span className="text-slate-400 border-b border-dotted border-slate-600 cursor-help">P/E Ratio</span>
                      </Tooltip>
                      <span className="text-white font-semibold">
                        {typeof stockHistory.pe_ratio === 'number' ? stockHistory.pe_ratio.toFixed(2) : stockHistory.pe_ratio}
                      </span>
                    </div>
                  )}

                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">24h Change</span>
                    <span className={`font-semibold ${isPriceUp ? 'text-emerald-400' : 'text-red-400'}`}>
                      {isPriceUp ? '+' : ''}{stockHistory.change_24h_pct.toFixed(2)}% (${stockHistory.change_24h.toFixed(2)})
                    </span>
                  </div>
                </div>
              )}

              {/* Score Reasons */}
              {scoreReasons && scoreReasons !== 'N/A' && (
                <div className="bg-slate-800/50 rounded-xl p-4">
                  <Tooltip text="Breakdown of why this stock got its Rainy Day Score.">
                    <div className="text-sm text-slate-400 mb-2 border-b border-dotted border-slate-600 inline-block cursor-help">Score Breakdown</div>
                  </Tooltip>
                  <div className="text-slate-200 text-sm leading-relaxed">{scoreReasons}</div>
                </div>
              )}

              {/* Analyst Targets */}
              {targetMeanPrice && !isNaN(targetMeanPrice) && (
                <div className="bg-linear-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-xl p-4">
                  <div className="text-slate-400 text-sm mb-2">Analyst Price Target</div>
                  <div className="text-white font-bold text-3xl">${targetMeanPrice.toFixed(2)}</div>
                  {currentPrice && (
                    <div className="text-slate-400 text-sm mt-1">
                      Current: ${currentPrice.toFixed(2)} • Potential: {upside}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StockDetail;
