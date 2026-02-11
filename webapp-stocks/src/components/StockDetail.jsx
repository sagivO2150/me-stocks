import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as ChartTooltip, ResponsiveContainer, Area, AreaChart, ComposedChart, Scatter } from 'recharts';
import Tooltip from './Tooltip';

const StockDetail = ({ trade, onClose }) => {
  const [stockHistory, setStockHistory] = useState(null);
  const [insiderTrades, setInsiderTrades] = useState(null);
  const [politicalTrades, setPoliticalTrades] = useState(null);
  const [loading, setLoading] = useState(true);
  const [insiderLoading, setInsiderLoading] = useState(true);
  const [politicalLoading, setPoliticalLoading] = useState(true);
  const [error, setError] = useState(null);
  const [period, setPeriod] = useState('1y'); // Start with 1 year as default
  const [useEdgarData, setUseEdgarData] = useState(false);
  const [edgarLoading, setEdgarLoading] = useState(false);
  const [edgarTrades, setEdgarTrades] = useState(null);
  const [edgarProgress, setEdgarProgress] = useState({ current: 0, total: 0, found: 0 });
  const [edgarStatus, setEdgarStatus] = useState('');
  const [focusDate, setFocusDate] = useState(''); // Empty by default, can be set to any date

  const ticker = trade.Ticker || trade.ticker;
  const isPoliticalTrade = trade.source === 'senate' || trade.source === 'house' || trade.politician;
  
  console.log('StockDetail opened with trade:', trade);
  console.log('Is political trade:', isPoliticalTrade);

  useEffect(() => {
    // When focus date is set, always ensure we have MAX data to cover any historical date
    if (focusDate) {
      // Always fetch MAX when a focus date is set to ensure we have enough historical data
      if (stockHistory?.history) {
        const firstAvailableDate = new Date(stockHistory.history[0].date.split('T')[0].split(' ')[0]);
        const lastAvailableDate = new Date(stockHistory.history[stockHistory.history.length - 1].date.split('T')[0].split(' ')[0]);
        const targetDate = new Date(focusDate + 'T00:00:00');
        
        console.log('Focus date:', targetDate.toISOString().split('T')[0]);
        console.log('Available range:', firstAvailableDate.toISOString().split('T')[0], 'to', lastAvailableDate.toISOString().split('T')[0]);
        
        // If focus date is outside current range, fetch MAX to get all available data
        if (targetDate < firstAvailableDate || targetDate > lastAvailableDate) {
          console.log('Focus date outside current range, fetching MAX period');
          fetchStockHistory('max');
          return;
        }
      } else {
        // No data yet, fetch MAX
        console.log('No stock history yet, fetching MAX to cover focus date');
        fetchStockHistory('max');
        return;
      }
    }
    
    // Normal period fetch when no focus date
    fetchStockHistory(period);
  }, [period, ticker, focusDate]);

  useEffect(() => {
    fetchInsiderTrades();
    fetchPoliticalTrades();
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

  const fetchEdgarTrades = async () => {
    setEdgarLoading(true);
    setEdgarProgress({ current: 0, total: 0, found: 0 });
    setEdgarStatus('Connecting to EDGAR...');
    
    try {
      const eventSource = new EventSource(`http://localhost:3001/api/edgar-trades/${ticker}`);
      
      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'progress') {
          setEdgarProgress({
            current: data.current,
            total: data.total,
            found: data.found
          });
        } else if (data.type === 'status') {
          setEdgarStatus(data.message);
        } else if (data.type === 'complete') {
          setEdgarTrades(data.data);
          setUseEdgarData(true);
          setEdgarLoading(false);
          setEdgarStatus('Complete!');
          eventSource.close();
        } else if (data.type === 'error') {
          console.error('Failed to fetch EDGAR data:', data.error);
          alert(`Failed to load EDGAR data: ${data.error}`);
          setEdgarLoading(false);
          setEdgarStatus('');
          eventSource.close();
        }
      };
      
      eventSource.onerror = (err) => {
        console.error('EventSource error:', err);
        alert('Failed to connect to server for EDGAR data');
        setEdgarLoading(false);
        setEdgarStatus('');
        eventSource.close();
      };
    } catch (err) {
      console.error('Failed to fetch EDGAR trades:', err);
      alert('Failed to connect to server for EDGAR data');
      setEdgarLoading(false);
      setEdgarStatus('');
    }
  };

  const fetchPoliticalTrades = async () => {
    setPoliticalLoading(true);
    
    try {
      const response = await fetch(`http://localhost:3001/api/political-trades/${ticker}`);
      const data = await response.json();
      
      if (data.success) {
        setPoliticalTrades(data);
      }
    } catch (err) {
      console.error('Failed to fetch political trades:', err);
    } finally {
      setPoliticalLoading(false);
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

  // Merge insider and political trades with stock history for chart display
  // Get the actual date range of available data
  const getAvailableDateRange = () => {
    if (!stockHistory || !stockHistory.history || stockHistory.history.length === 0) {
      return null;
    }
    
    const firstDate = new Date(stockHistory.history[0].date);
    const lastDate = new Date(stockHistory.history[stockHistory.history.length - 1].date);
    const dataPoints = stockHistory.history.length;
    
    // For intraday data (same day), calculate hours instead of days
    const isIntraday = stockHistory.history[0].date.includes(':');
    
    return { firstDate, lastDate, dataPoints, isIntraday };
  };

  // All periods are always available - clicking a button will fetch that period's data
  const hasDataForPeriod = (periodString) => {
    return true;
  };

  // Classify insider role from title - MUST match openinsider_scraper.py classification
  const classifyInsiderRole = (title) => {
    if (!title) return 'Other';
    
    const titleLower = title.toLowerCase();
    
    // Priority order (same as scraper):
    // 1. COB/Chairman
    if (titleLower.includes('cob') || titleLower.includes('chairman')) return 'C-Level';
    
    // 2. CEO
    if (titleLower.includes('ceo') || titleLower.includes('chief executive')) return 'C-Level';
    
    // 3. President (but not VP)
    if ((titleLower.includes('pres') || titleLower.includes('president')) && 
        !titleLower.includes('vp') && !titleLower.includes('vice')) return 'C-Level';
    
    // 4. CFO
    if (titleLower.includes('cfo') || titleLower.includes('chief financial')) return 'C-Level';
    
    // 5. COO
    if (titleLower.includes('coo') || titleLower.includes('chief operating')) return 'C-Level';
    
    // 6. General Counsel
    if (titleLower.includes('gc') || titleLower.includes('general counsel')) return 'C-Level';
    
    // 7. VP
    if (titleLower.includes('vp') || titleLower.includes('vice pres')) return 'C-Level';
    
    // 8. Director (must check BEFORE checking for "dir" alone)
    if (titleLower.includes('dir') || titleLower.includes('director')) return 'Director';
    
    // 9. 10% owners
    if (title.includes('10%') || titleLower.includes('beneficial')) return '10% Owner';
    
    // 10. Everything else
    return 'Other';
  };

  // Calculate smart X-axis ticks based on period (like Google Finance)
  const getXAxisTicks = () => {
    const chartData = mergedChartData();
    if (!chartData || chartData.length === 0) return [];
    
    const totalPoints = chartData.length;
    
    // If focus date is set, adjust tick counts for better visibility in zoomed view
    if (focusDate) {
      const focusTickCounts = {
        '1d': 6,   // 6 time points for single day
        '5d': 5,   // 5 date points
        '1mo': 6,  // 6 date points
        '3mo': 6,  // 6 points
        '6mo': 6,  // 6 points
        '1y': 12,  // 12 points (monthly)
        '2y': 12,  // 12 points
        '5y': 10   // 10 points
      };
      const targetCount = focusTickCounts[period] || 6;
      
      if (totalPoints <= targetCount) {
        return chartData.map(p => p.date);
      }
      
      // For 1Y with focus, try to show month boundaries
      if (period === '1y') {
        const monthBoundaries = [];
        let lastMonth = null;
        
        chartData.forEach((point) => {
          const date = new Date(point.date);
          const monthKey = `${date.getFullYear()}-${date.getMonth()}`;
          if (lastMonth !== monthKey) {
            monthBoundaries.push(point.date);
            lastMonth = monthKey;
          }
        });
        
        // If we have too many month boundaries, sample them evenly
        if (monthBoundaries.length > targetCount) {
          const step = Math.floor(monthBoundaries.length / targetCount);
          const sampledTicks = [];
          for (let i = 0; i < targetCount; i++) {
            const idx = Math.min(i * step, monthBoundaries.length - 1);
            sampledTicks.push(monthBoundaries[idx]);
          }
          return sampledTicks;
        }
        
        return monthBoundaries.length > 0 ? monthBoundaries : [chartData[Math.floor(totalPoints / 2)].date];
      }
      
      // For other periods, evenly space the ticks
      const step = Math.floor(totalPoints / targetCount);
      const ticks = [];
      for (let i = 0; i < targetCount; i++) {
        const idx = Math.min(i * step, totalPoints - 1);
        ticks.push(chartData[idx].date);
      }
      return ticks;
    }
    
    // Original logic for non-focused view
    // Define target tick counts per period
    const tickCounts = {
      '1d': 6,   // 6 time points
      '5d': 4,   // 4 date points
      '1m': 7,   // 7 date points
      '3m': 5,   // 5 points
      '6m': 3,   // 3 points
      '1y': 1,   // 1 point (year change)
      '2y': 2,   // 2 points (year changes)
      '5y': 5,   // 5 points (year changes)
      'max': 6   // Up to 6 evenly spaced years
    };
    
    const targetCount = tickCounts[period] || 6;
    
    // For 1Y, 2Y, 5Y - find year boundaries
    if (['1y', '2y', '5y'].includes(period)) {
      const yearBoundaries = [];
      let lastYear = null;
      
      chartData.forEach((point, idx) => {
        const date = new Date(point.date);
        const year = date.getFullYear();
        if (lastYear !== null && year !== lastYear) {
          yearBoundaries.push(point.date);
        }
        lastYear = year;
      });
      
      return yearBoundaries.length > 0 ? yearBoundaries : [chartData[Math.floor(totalPoints / 2)].date];
    }
    
    // For Max - space out years evenly
    if (period === 'max') {
      const firstDate = new Date(chartData[0].date);
      const lastDate = new Date(chartData[totalPoints - 1].date);
      const yearSpan = lastDate.getFullYear() - firstDate.getFullYear();
      
      if (yearSpan >= 6) {
        const yearGap = Math.ceil(yearSpan / 6);
        const ticks = [];
        let currentYear = firstDate.getFullYear();
        
        chartData.forEach(point => {
          const pointYear = new Date(point.date).getFullYear();
          if (pointYear >= currentYear) {
            ticks.push(point.date);
            currentYear += yearGap;
          }
        });
        
        return ticks.slice(0, 6);
      }
    }
    
    // For other periods - evenly space points
    if (totalPoints <= targetCount) {
      return chartData.map(p => p.date);
    }
    
    const step = Math.floor(totalPoints / targetCount);
    const ticks = [];
    for (let i = 0; i < targetCount; i++) {
      const idx = Math.min(i * step, totalPoints - 1);
      ticks.push(chartData[idx].date);
    }
    
    return ticks;
  };

  const mergedChartData = () => {
    if (!stockHistory || !stockHistory.history) return [];
    
    console.log('Building merged chart data...');
    console.log('Political trades:', politicalTrades);
    
    let data = [...stockHistory.history];
    
    // Apply date-based filtering if focusDate is set
    if (focusDate) {
      console.log('Focus date set:', focusDate, 'Period:', period);
      console.log('Data before filter:', data.length, 'points');
      if (data.length > 0) {
        console.log('First data point:', data[0].date, 'Last data point:', data[data.length - 1].date);
      }
      
      const centerDate = new Date(focusDate + 'T00:00:00'); // Ensure we're at midnight UTC
      const rangeInDays = {
        '1d': 0,
        '5d': 5,
        '1mo': 30,
        '3mo': 90,
        '6mo': 180,
        '1y': 365,
        '2y': 730,
        '5y': 1825,
        'max': null // Don't filter for max
      }[period];
      
      console.log('Range in days:', rangeInDays, 'Center date:', centerDate.toISOString());
      
      if (rangeInDays !== null && rangeInDays !== undefined) {
        // For 1 day, show that specific day only
        if (period === '1d') {
          data = data.filter(point => {
            // Extract just the date part (YYYY-MM-DD) regardless of format
            const dateStr = point.date.split('T')[0].split(' ')[0];
            const pointDate = new Date(dateStr + 'T00:00:00');
            const isSameDay = pointDate.getFullYear() === centerDate.getFullYear() &&
                              pointDate.getMonth() === centerDate.getMonth() &&
                              pointDate.getDate() === centerDate.getDate();
            return isSameDay;
          });
        } else {
          // For other ranges, show data CENTERED around the focus date
          // Calculate start and end dates
          const halfRange = rangeInDays / 2;
          const startDate = new Date(centerDate);
          startDate.setDate(startDate.getDate() - halfRange);
          const endDate = new Date(centerDate);
          endDate.setDate(endDate.getDate() + halfRange);
          
          console.log('Date range (centered):', 
            startDate.toISOString().split('T')[0], 
            'to', 
            endDate.toISOString().split('T')[0],
            '(center:', centerDate.toISOString().split('T')[0], ')');
          
          data = data.filter(point => {
            // Extract just the date part (YYYY-MM-DD) regardless of format
            const dateStr = point.date.split('T')[0].split(' ')[0];
            const pointDate = new Date(dateStr + 'T00:00:00');
            const isInRange = pointDate >= startDate && pointDate <= endDate;
            return isInRange;
          });
        }
        
        console.log(`Focus date filter applied: ${data.length} data points in range`);
        if (data.length > 0) {
          console.log('Filtered first:', data[0].date, 'Filtered last:', data[data.length - 1].date);
        }
        
        // If filtering resulted in no data, show a warning
        if (data.length === 0) {
          console.warn('No data points found in the selected range. Try a wider period or different date.');
        }
      }
    }
    
    // Use EDGAR data if loaded, otherwise use OpenInsider data
    const activeInsiderTrades = useEdgarData && edgarTrades ? edgarTrades : insiderTrades;
    
    // Create maps for insider purchases and sales by date - KEEP INDIVIDUAL TRADES
    const insiderPurchasesByDate = {};
    const insiderSalesByDate = {};
    
    if (activeInsiderTrades) {
      console.log('Processing insider trades...');
      activeInsiderTrades.purchases?.forEach(trade => {
        // Normalize date to YYYY-MM-DD format
        const dateKey = trade.date.split('T')[0].split(' ')[0];
        console.log('Insider purchase date:', trade.date, '-> normalized:', dateKey);
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
      
      activeInsiderTrades.sales?.forEach(trade => {
        // Normalize date to YYYY-MM-DD format
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
      
      console.log('Insider purchases by date:', Object.keys(insiderPurchasesByDate));
    }
    
    // Create maps for political purchases and sales by date
    const politicalPurchasesByDate = {};
    const politicalSalesByDate = {};
    
    if (politicalTrades) {
      console.log('Processing political purchases:', politicalTrades.purchases);
      politicalTrades.purchases?.forEach(trade => {
        const dateKey = trade.trade_date; // Use trade_date field
        console.log('Mapping political purchase:', trade.politician, dateKey, trade.amount_value);
        if (!politicalPurchasesByDate[dateKey]) {
          politicalPurchasesByDate[dateKey] = { value: 0, count: 0, politicians: [] };
        }
        politicalPurchasesByDate[dateKey].value += parseFloat(trade.amount_value) || 0;
        politicalPurchasesByDate[dateKey].count += 1;
        politicalPurchasesByDate[dateKey].politicians.push(trade.politician);
      });
      console.log('Political purchases by date map:', politicalPurchasesByDate);
      
      politicalTrades.sales?.forEach(trade => {
        const dateKey = trade.trade_date; // Use trade_date field  
        console.log('Mapping political sale:', trade.politician, dateKey, trade.amount_value);
        if (!politicalSalesByDate[dateKey]) {
          politicalSalesByDate[dateKey] = { value: 0, count: 0, politicians: [] };
        }
        politicalSalesByDate[dateKey].value += parseFloat(trade.amount_value) || 0;
        politicalSalesByDate[dateKey].count += 1;
        politicalSalesByDate[dateKey].politicians.push(trade.politician);
      });
      console.log('Political sales by date map:', politicalSalesByDate);
    }
    
    // Merge with stock data
    return data.map(point => {
      // Normalize stock history date to YYYY-MM-DD format
      const dateKey = point.date.split('T')[0].split(' ')[0];
      
      console.log('Stock data point:', point.date, '-> normalized:', dateKey, 
        'Has purchases?', !!insiderPurchasesByDate[dateKey], 
        'Has sales?', !!insiderSalesByDate[dateKey]);
      
      // For intraday data, aggregate all trades for that day on the first data point of the day
      const isFirstPointOfDay = !data.find(p => {
        const pDate = p.date.split('T')[0].split(' ')[0];
        return pDate === dateKey && data.indexOf(p) < data.indexOf(point);
      });
      
      return {
        ...point,
        // Insider data - store individual trades list and totals
        purchases: (point.date.includes(':') && !isFirstPointOfDay) ? 0 : (insiderPurchasesByDate[dateKey]?.totalValue || 0),
        sales: (point.date.includes(':') && !isFirstPointOfDay) ? 0 : (insiderSalesByDate[dateKey]?.totalValue || 0),
        purchaseCount: (point.date.includes(':') && !isFirstPointOfDay) ? 0 : (insiderPurchasesByDate[dateKey]?.count || 0),
        saleCount: (point.date.includes(':') && !isFirstPointOfDay) ? 0 : (insiderSalesByDate[dateKey]?.count || 0),
        purchaseTrades: (point.date.includes(':') && !isFirstPointOfDay) ? [] : (insiderPurchasesByDate[dateKey]?.trades || []),
        saleTrades: (point.date.includes(':') && !isFirstPointOfDay) ? [] : (insiderSalesByDate[dateKey]?.trades || []),
        // Political data
        politicalPurchases: (point.date.includes(':') && !isFirstPointOfDay) ? 0 : (politicalPurchasesByDate[dateKey]?.value || 0),
        politicalSales: (point.date.includes(':') && !isFirstPointOfDay) ? 0 : (politicalSalesByDate[dateKey]?.value || 0),
        politicalPurchaseCount: (point.date.includes(':') && !isFirstPointOfDay) ? 0 : (politicalPurchasesByDate[dateKey]?.count || 0),
        politicalSaleCount: (point.date.includes(':') && !isFirstPointOfDay) ? 0 : (politicalSalesByDate[dateKey]?.count || 0),
        politicians: [
          ...(politicalPurchasesByDate[dateKey]?.politicians || []),
          ...(politicalSalesByDate[dateKey]?.politicians || [])
        ]
      };
    });
  };

  // Custom tooltip for chart - show individual trade when hovering a dot, or all trades for a date
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      
      // Check if this is a single trade (from Scatter) with insider_name
      if (data.insider_name) {
        const isPurchase = data.type !== 'Sale';
        return (
          <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-xl">
            <p className="text-slate-300 text-sm font-semibold mb-2">{data.date}</p>
            <div className="space-y-1">
              <p className={`text-xs font-semibold ${isPurchase ? 'text-emerald-400' : 'text-red-400'}`}>
                {isPurchase ? '📈' : '📉'} {data.role} {isPurchase ? 'Purchase' : 'Sale'}
              </p>
              <p className="text-xs text-slate-300">👤 {data.insider_name}</p>
              <p className="text-xs text-slate-400">💼 {data.title}</p>
              <p className={`text-xs font-bold ${isPurchase ? 'text-emerald-300' : 'text-red-300'}`}>
                💰 ${data.value >= 1000000 ? (data.value / 1000000).toFixed(2) + 'M' : (data.value / 1000).toFixed(0) + 'K'}
              </p>
              <p className="text-xs text-slate-400">
                📊 {data.shares.toLocaleString()} shares
              </p>
            </div>
          </div>
        );
      }
      
      // Otherwise show aggregated data for the date (for political or when hovering the line)
      const hasInsiderActivity = data.purchaseCount > 0 || data.saleCount > 0;
      const hasPoliticalActivity = data.politicalPurchaseCount > 0 || data.politicalSaleCount > 0;
      
      // Only show tooltip if there's actual trade activity
      if (!hasInsiderActivity && !hasPoliticalActivity) {
        return null;
      }
      
      return (
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-xl max-h-96 overflow-y-auto">
          <p className="text-slate-300 text-sm font-semibold mb-2 sticky top-0 bg-slate-800">{data.date}</p>
          
          {/* Insider Activity - Show EACH trade individually */}
          {hasInsiderActivity && (
            <div className="mb-2 space-y-2">
              {data.purchaseTrades && data.purchaseTrades.length > 0 && (
                <div>
                  <p className="text-xs text-emerald-400 font-semibold mb-1">
                    🏢 Purchases ({data.purchaseCount})
                  </p>
                  <div className="pl-2 space-y-1.5">
                    {data.purchaseTrades.map((trade, idx) => (
                      <div key={`purchase-${idx}`} className="text-xs border-l-2 border-emerald-500 pl-2 py-1">
                        <p className="text-emerald-300 font-semibold">{trade.role} - ${trade.value >= 1000000 ? (trade.value / 1000000).toFixed(2) + 'M' : (trade.value / 1000).toFixed(0) + 'K'}</p>
                        <p className="text-slate-300">{trade.insider}</p>
                        <p className="text-slate-400 text-[10px]">{trade.title} • {trade.shares.toLocaleString()} shares</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {data.saleTrades && data.saleTrades.length > 0 && (
                <div className={data.purchaseTrades && data.purchaseTrades.length > 0 ? 'mt-2' : ''}>
                  <p className="text-xs text-red-400 font-semibold mb-1">
                    🏢 Sales ({data.saleCount})
                  </p>
                  <div className="pl-2 space-y-1.5">
                    {data.saleTrades.map((trade, idx) => (
                      <div key={`sale-${idx}`} className="text-xs border-l-2 border-red-500 pl-2 py-1">
                        <p className="text-red-300 font-semibold">{trade.role} - ${trade.value >= 1000000 ? (trade.value / 1000000).toFixed(2) + 'M' : (trade.value / 1000).toFixed(0) + 'K'}</p>
                        <p className="text-slate-300">{trade.insider}</p>
                        <p className="text-slate-400 text-[10px]">{trade.title} • {trade.shares.toLocaleString()} shares</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          
          {/* Political Activity */}
          {hasPoliticalActivity && (
            <div className={hasInsiderActivity ? "border-t border-slate-700 pt-2" : ""}>
              <p className="text-xs text-blue-400 font-semibold mb-1">🏛️ Political Trades</p>
              {data.politicalPurchaseCount > 0 && (
                <p className="text-xs text-blue-300">
                  📈 {data.politicalPurchaseCount} purchase{data.politicalPurchaseCount > 1 ? 's' : ''} (${data.politicalPurchases >= 1000000 ? (data.politicalPurchases / 1000000).toFixed(1) + 'M' : (data.politicalPurchases / 1000).toFixed(0) + 'K'})
                </p>
              )}
              {data.politicalSaleCount > 0 && (
                <p className="text-xs text-red-300">
                  📉 {data.politicalSaleCount} sale{data.politicalSaleCount > 1 ? 's' : ''} (${data.politicalSales >= 1000000 ? (data.politicalSales / 1000000).toFixed(1) + 'M' : (data.politicalSales / 1000).toFixed(0) + 'K'})
                </p>
              )}
              {data.politicians && data.politicians.length > 0 && (
                <p className="text-xs text-slate-400 mt-1">
                  by {data.politicians.slice(0, 2).join(', ')}{data.politicians.length > 2 ? ` +${data.politicians.length - 2} more` : ''}
                </p>
              )}
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
          {/* Period Selector with Date Picker */}
          <div className="mb-6">
            <div className="flex gap-2 flex-wrap items-center">
              {['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'].map((p) => {
                return (
                  <button
                    key={p}
                    onClick={() => setPeriod(p)}
                    disabled={loading}
                    className={`px-4 py-2 rounded-lg transition-all ${
                      period === p
                        ? 'bg-blue-600 text-white'
                        : loading
                        ? 'bg-slate-800/30 text-slate-600 cursor-not-allowed'
                        : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white'
                    }`}
                  >
                    {loading && period === p ? '⏳' : (p === 'max' ? 'MAX' : p.toUpperCase())}
                  </button>
                );
              })}
              
              {/* Date Picker for Focus Date */}
              <div className="flex items-center gap-2 ml-2">
                <span className="text-slate-400 text-sm">Focus:</span>
                <input
                  type="date"
                  value={focusDate}
                  onChange={(e) => setFocusDate(e.target.value)}
                  min={stockHistory?.history?.[0]?.date.split('T')[0].split(' ')[0]}
                  max={stockHistory?.history?.[stockHistory.history.length - 1]?.date.split('T')[0].split(' ')[0]}
                  className="px-3 py-2 bg-slate-700 text-white rounded-lg border border-slate-600 focus:border-purple-500 focus:outline-none text-sm"
                  placeholder="Today"
                />
                {focusDate && (
                  <button
                    onClick={() => setFocusDate('')}
                    className="px-3 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg transition-all text-sm"
                    title="Clear focus date"
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>
            
            {focusDate && (
              <div className="mt-2 text-sm text-purple-400">
                📍 Viewing {period.toUpperCase()} around {new Date(focusDate).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}
                {(() => {
                  const chartData = mergedChartData();
                  if (chartData.length > 0) {
                    const firstDate = chartData[0].date.split('T')[0].split(' ')[0];
                    const lastDate = chartData[chartData.length - 1].date.split('T')[0].split(' ')[0];
                    return (
                      <span className="ml-2 text-xs text-slate-500">
                        (Showing: {new Date(firstDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} - {new Date(lastDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })})
                      </span>
                    );
                  }
                  return null;
                })()}
              </div>
            )}
            
            {/* EDGAR Historical Data Button */}
            <div className="mt-3 flex items-center gap-3">
              {!useEdgarData ? (
                <div className="flex flex-col gap-2 w-full">
                  <button
                    onClick={fetchEdgarTrades}
                    disabled={edgarLoading}
                    className={`px-4 py-2 rounded-lg font-medium transition-all ${
                      edgarLoading
                        ? 'bg-slate-700 text-slate-500 cursor-wait'
                        : 'bg-green-600 text-white hover:bg-green-500'
                    }`}
                  >
                    {edgarLoading ? (
                      <>
                        <span className="inline-block animate-spin mr-2">⏳</span>
                        Loading Historical Data (EDGAR)...
                      </>
                    ) : (
                      <>
                        📈 Load Extended History (5 Years - EDGAR)
                      </>
                    )}
                  </button>
                  
                  {/* Progress Indicator */}
                  {edgarLoading && (
                    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-3">
                      {edgarStatus && (
                        <div className="text-slate-400 text-sm mb-2">
                          {edgarStatus}
                        </div>
                      )}
                      {edgarProgress.total > 0 && (
                        <div className="space-y-2">
                          <div className="flex justify-between items-center text-sm">
                            <span className="text-emerald-400 font-mono font-bold">
                              {edgarProgress.current}/{edgarProgress.total}
                            </span>
                            <span className="text-slate-400">
                              Found {edgarProgress.found} transactions
                            </span>
                          </div>
                          <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
                            <div 
                              className="bg-emerald-500 h-full transition-all duration-300 ease-out"
                              style={{ width: `${(edgarProgress.current / edgarProgress.total) * 100}%` }}
                            ></div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="px-3 py-1 bg-green-600/20 border border-green-600/50 rounded-lg text-green-400 text-sm font-medium">
                    ✓ Extended Historical Data Loaded ({edgarTrades?.total_purchases + edgarTrades?.total_sales || 0} trades)
                  </span>
                  <button
                    onClick={() => { setUseEdgarData(false); setEdgarTrades(null); }}
                    className="px-3 py-1 bg-slate-700 text-slate-400 hover:bg-slate-600 hover:text-white rounded-lg text-sm transition-all"
                  >
                    Use OpenInsider Only
                  </button>
                </div>
              )}
              {!useEdgarData && (
                <span className="text-slate-500 text-sm">
                  Current data: ~2 years from OpenInsider
                </span>
              )}
            </div>
            
            {/* Show limited data warning */}
            {(() => {
              const range = getAvailableDateRange();
              if (!range) return null;
              
              const { firstDate, lastDate, dataPoints, isIntraday } = range;
              
              // For intraday data, don't calculate days - just show we're in intraday mode
              if (isIntraday) {
                return null; // No warning for intraday data
              }
              
              const daysDiff = Math.floor((lastDate - firstDate) / (1000 * 60 * 60 * 24));
              
              // Only show warning if viewing MAX period and still have less than 60 days
              // (This means the stock is genuinely new, not just a short period selection)
              if (period === 'max' && daysDiff < 60) {
                return (
                  <div className="mt-3 px-4 py-2 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                    <p className="text-yellow-400 text-sm">
                      ⚠️ Limited historical data available: Only {daysDiff} days since {firstDate.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}
                      {daysDiff < 30 && ' (Recently IPO\'d stock)'}
                    </p>
                  </div>
                );
              }
              
              return null;
            })()}
          </div>

          {/* Chart */}
          <div 
            className="bg-slate-800/50 rounded-xl p-6 mb-6" 
            style={{ userSelect: 'none' }}
            onMouseEnter={() => {
              if (document.activeElement) {
                document.activeElement.blur();
              }
            }}
            onMouseDown={(e) => {
              e.preventDefault();
              return false;
            }}
          >
            {/* Trade Activity Legend */}
            {((insiderTrades && (insiderTrades.total_purchases > 0 || insiderTrades.total_sales > 0)) || 
              (edgarTrades && useEdgarData && (edgarTrades.total_purchases > 0 || edgarTrades.total_sales > 0)) ||
              (politicalTrades && (politicalTrades.purchases?.length > 0 || politicalTrades.sales?.length > 0))) && (
              <div className="flex justify-center gap-4 mb-4 text-sm flex-wrap">
                {/* Use EDGAR counts if loaded, otherwise OpenInsider counts */}
                {((useEdgarData && edgarTrades && edgarTrades.total_purchases > 0) || 
                  (!useEdgarData && insiderTrades && insiderTrades.total_purchases > 0)) && (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-0.5 bg-emerald-400"></div>
                    <span className="text-slate-300">
                      🏢 Insider Purchases ({(() => {
                        // Count visible purchases in filtered data
                        const chartData = mergedChartData();
                        const visibleCount = chartData.filter(d => d.purchaseCount > 0).reduce((sum, d) => sum + d.purchaseCount, 0);
                        const totalCount = (useEdgarData && edgarTrades) ? edgarTrades.total_purchases : insiderTrades.total_purchases;
                        return focusDate && visibleCount < totalCount ? `${visibleCount}/${totalCount}` : totalCount;
                      })()})
                      {useEdgarData && <span className="ml-1 text-green-400 text-xs">(EDGAR)</span>}
                    </span>
                  </div>
                )}
                {((useEdgarData && edgarTrades && edgarTrades.total_sales > 0) || 
                  (!useEdgarData && insiderTrades && insiderTrades.total_sales > 0)) && (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-0.5 bg-red-500" style={{backgroundImage: 'repeating-linear-gradient(90deg, #ef4444 0, #ef4444 3px, transparent 3px, transparent 6px)'}}></div>
                    <span className="text-slate-300">
                      🏢 Insider Sales ({(() => {
                        // Count visible sales in filtered data
                        const chartData = mergedChartData();
                        const visibleCount = chartData.filter(d => d.saleCount > 0).reduce((sum, d) => sum + d.saleCount, 0);
                        const totalCount = (useEdgarData && edgarTrades) ? edgarTrades.total_sales : insiderTrades.total_sales;
                        return focusDate && visibleCount < totalCount ? `${visibleCount}/${totalCount}` : totalCount;
                      })()})
                      {useEdgarData && <span className="ml-1 text-green-400 text-xs">(EDGAR)</span>}
                    </span>
                  </div>
                )}
                {politicalTrades && politicalTrades.purchases?.length > 0 && (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-0.5 bg-blue-400"></div>
                    <span className="text-slate-300">
                      🏛️ Political Purchases ({politicalTrades.purchases.length})
                    </span>
                  </div>
                )}
                {politicalTrades && politicalTrades.sales?.length > 0 && (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-0.5 bg-purple-500" style={{backgroundImage: 'repeating-linear-gradient(90deg, #a855f7 0, #a855f7 3px, transparent 3px, transparent 6px)'}}></div>
                    <span className="text-slate-300">
                      🏛️ Political Sales ({politicalTrades.sales.length})
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
            
            {!loading && !error && mergedChartData().length === 0 && (
              <div className="h-96 flex items-center justify-center">
                <div className="bg-yellow-900/30 border border-yellow-700 rounded-lg p-6 max-w-2xl">
                  <div className="text-yellow-300 text-xl mb-2">⚠️ No Data in Selected Range</div>
                  <div className="text-yellow-200 text-sm">
                    <p className="mb-2">No chart data available for the selected focus date and time range.</p>
                    {focusDate && (
                      <p className="text-xs text-yellow-300/70 mt-1">
                        Try selecting a different date, or clear the focus date to view all available data.
                        <br />The current stock history may not extend back to {new Date(focusDate).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
            
            {error && (
              <div className="h-96 flex items-center justify-center">
                <div className="bg-yellow-900/30 border border-yellow-700 rounded-lg p-6 max-w-2xl">
                  <div className="text-yellow-300 text-xl mb-2">⚠️ Price Data Unavailable</div>
                  <div className="text-yellow-200 text-sm">
                    {error.includes('delisted') || error.includes('No data found') ? (
                      <>
                        <p className="mb-2">This ticker may be a warrant, delisted, or have no trading data.</p>
                        <p className="text-xs text-yellow-300/70 mt-1">
                          Note: Warrants (symbols ending in 'W') often lack price history on Yahoo Finance.
                        </p>
                      </>
                    ) : (
                      <p>{error}</p>
                    )}
                  </div>
                  <div className="text-yellow-300 text-xs mt-3">
                    📊 Insider trade data is still available below
                  </div>
                </div>
              </div>
            )}
            
            {!loading && !error && stockHistory && stockHistory.history && (
              <ResponsiveContainer width="100%" height={400}>
                <ComposedChart 
                  data={mergedChartData()} 
                  margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                >
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
                    ticks={getXAxisTicks()}
                    tickFormatter={(value) => {
                      const date = new Date(value);
                      
                      // For intraday data (1D), show time
                      if (period === '1d' && value.includes(':')) {
                        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
                      }
                      
                      // For 5D and 1M, show day + month
                      if (period === '5d' || period === '1mo') {
                        return `${date.getDate()} ${date.toLocaleString('en-US', { month: 'short' })}`;
                      }
                      
                      // For 3M and 6M, show month + year
                      if (period === '3mo' || period === '6mo') {
                        return date.toLocaleString('en-US', { month: 'short', year: 'numeric' });
                      }
                      
                      // For 1Y - show month + year when focus date is set, otherwise just year
                      if (period === '1y') {
                        if (focusDate) {
                          return date.toLocaleString('en-US', { month: 'short', year: '2-digit' });
                        }
                        return date.getFullYear().toString();
                      }
                      
                      // For 2Y, 5Y, Max - show year only
                      return date.getFullYear().toString();
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
                  <ChartTooltip 
                    content={<CustomTooltip />} 
                    cursor={{ stroke: '#475569', strokeWidth: 1, strokeDasharray: '3 3' }}
                    allowEscapeViewBox={{ x: false, y: false }}
                    wrapperStyle={{ zIndex: 1000, outline: 'none', pointerEvents: 'none' }}
                  />
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
                      isAnimationActive={false}
                      strokeDasharray="3 3"
                      dot={(dotProps) => {
                        const { cx, cy, payload } = dotProps;
                        if (!payload || !payload.purchaseTrades || payload.purchaseTrades.length === 0) {
                          return <circle key={`purchase-empty-${cx}-${cy}`} cx={cx} cy={cy} r={0} fill="none" />;
                        }
                        
                        // Render multiple dots if there are multiple trades
                        const trades = payload.purchaseTrades;
                        const numTrades = trades.length;
                        
                        if (numTrades === 1) {
                          // Single trade - one dot
                          return <circle key={`purchase-${cx}-${cy}`} cx={cx} cy={cy} r={8} fill="#10b981" stroke="#fff" strokeWidth={2} />;
                        } else {
                          // Multiple trades - render multiple dots with x-offset
                          const spacing = 4;
                          const startX = cx - ((numTrades - 1) * spacing) / 2;
                          return (
                            <g key={`purchase-group-${cx}-${cy}`}>
                              {trades.map((trade, idx) => (
                                <circle
                                  key={`purchase-${cx}-${cy}-${idx}`}
                                  cx={startX + (idx * spacing)}
                                  cy={cy}
                                  r={7}
                                  fill="#10b981"
                                  stroke="#fff"
                                  strokeWidth={2}
                                />
                              ))}
                            </g>
                          );
                        }
                      }}
                      activeDot={(dotProps) => {
                        const { cx, cy, payload } = dotProps;
                        if (payload && payload.purchases > 0) {
                          return <circle key={`purchase-active-${cx}-${cy}`} cx={cx} cy={cy} r={12} fill="#10b981" stroke="#fff" strokeWidth={3} />;
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
                      isAnimationActive={false}
                      dot={(dotProps) => {
                        const { cx, cy, payload } = dotProps;
                        if (!payload || !payload.saleTrades || payload.saleTrades.length === 0) {
                          return <circle key={`sale-empty-${cx}-${cy}`} cx={cx} cy={cy} r={0} fill="none" />;
                        }
                        
                        // Render multiple dots if there are multiple trades
                        const trades = payload.saleTrades;
                        const numTrades = trades.length;
                        
                        if (numTrades === 1) {
                          // Single trade - one dot
                          return <circle key={`sale-${cx}-${cy}`} cx={cx} cy={cy} r={8} fill="#ef4444" stroke="#fff" strokeWidth={2} />;
                        } else {
                          // Multiple trades - render multiple dots with x-offset
                          const spacing = 4;
                          const startX = cx - ((numTrades - 1) * spacing) / 2;
                          return (
                            <g key={`sale-group-${cx}-${cy}`}>
                              {trades.map((trade, idx) => (
                                <circle
                                  key={`sale-${cx}-${cy}-${idx}`}
                                  cx={startX + (idx * spacing)}
                                  cy={cy}
                                  r={7}
                                  fill="#ef4444"
                                  stroke="#fff"
                                  strokeWidth={2}
                                />
                              ))}
                            </g>
                          );
                        }
                      }}
                      activeDot={(dotProps) => {
                        const { cx, cy, payload } = dotProps;
                        if (payload && payload.sales > 0) {
                          return <circle key={`sale-active-${cx}-${cy}`} cx={cx} cy={cy} r={12} fill="#ef4444" stroke="#fff" strokeWidth={3} />;
                        }
                        return false;
                      }}
                    />
                  )}
                  {politicalTrades && politicalTrades.purchases?.length > 0 && (
                    <Scatter
                      yAxisId="price"
                      dataKey="politicalPurchases"
                      fill="#3b82f6"
                      isAnimationActive={false}
                      shape={(props) => {
                        const { cx, cy, payload } = props;
                        if (!payload || payload.politicalPurchases <= 0) return null;
                        // Use the close price for positioning
                        const priceY = cy;
                        return (
                          <g>
                            <rect x={cx - 10} y={priceY - 10} width={20} height={20} fill="#3b82f6" stroke="#fff" strokeWidth={3} />
                            <text x={cx} y={priceY - 20} textAnchor="middle" fill="#3b82f6" fontSize="20" fontWeight="bold">🏛️</text>
                          </g>
                        );
                      }}
                    />
                  )}
                  {politicalTrades && politicalTrades.sales?.length > 0 && (
                    <Scatter
                      yAxisId="price"
                      dataKey="politicalSales"
                      fill="#a855f7"
                      isAnimationActive={false}
                      shape={(props) => {
                        const { cx, cy, payload } = props;
                        if (!payload || payload.politicalSales <= 0) return null;
                        const priceY = cy;
                        return (
                          <g>
                            <rect x={cx - 10} y={priceY - 10} width={20} height={20} fill="#a855f7" stroke="#fff" strokeWidth={3} transform={`rotate(45 ${cx} ${priceY})`} />
                            <text x={cx} y={priceY - 20} textAnchor="middle" fill="#a855f7" fontSize="20" fontWeight="bold">🏛️</text>
                          </g>
                        );
                      }}
                    />
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Two Column Layout for Details */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Column: Trade Info */}
            <div className="space-y-4">
              <h3 className="text-xl font-bold text-white mb-4">
                {isPoliticalTrade ? '🏛️ Political Trade Details' : 'Insider Trade Details'}
              </h3>
              
              {isPoliticalTrade ? (
                /* Political Trade Details */
                <>
                  {/* Political Trade Badges */}
                  <div className="flex flex-wrap gap-2">
                    <span className="px-3 py-2 bg-blue-500/20 text-blue-400 rounded-lg text-sm font-medium border border-blue-500/30">
                      🏛️ {trade.politician}
                    </span>
                    <span className={`px-3 py-2 rounded-lg text-sm font-medium border ${
                      trade.party === 'Democrat' ? 'bg-blue-500/20 text-blue-400 border-blue-500/30' :
                      trade.party === 'Republican' ? 'bg-red-500/20 text-red-400 border-red-500/30' :
                      'bg-gray-500/20 text-gray-400 border-gray-500/30'
                    }`}>
                      {trade.party} • {trade.state || trade.district}
                    </span>
                    {trade.committee && (
                      <span className="px-3 py-2 bg-purple-500/20 text-purple-400 rounded-lg text-sm font-medium border border-purple-500/30">
                        ⚖️ {trade.committee}
                      </span>
                    )}
                  </div>

                  {/* Political Trade Stats */}
                  <div className="bg-slate-800/50 rounded-xl p-4 space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Transaction Type</span>
                      <span className={`font-semibold text-lg ${
                        trade.trade_type === 'Purchase' ? 'text-emerald-400' : 'text-red-400'
                      }`}>
                        {trade.trade_type}
                      </span>
                    </div>
                    
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Amount Range</span>
                      <span className="text-white font-semibold">{trade.amount_range}</span>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Estimated Value</span>
                      <span className="text-white font-semibold text-lg">
                        ${(parseFloat(trade.amount_value) / 1000000).toFixed(1)}M
                      </span>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Trade Date</span>
                      <span className="text-white font-semibold">{trade.trade_date}</span>
                    </div>
                  </div>

                  {/* Other Politicians Trading This Stock */}
                  {politicalTrades && (politicalTrades.purchases?.length > 0 || politicalTrades.sales?.length > 0) && (
                    <div className="bg-slate-800/50 rounded-xl p-4">
                      <div className="text-sm text-slate-400 mb-3 font-semibold">Other Political Activity on {ticker}</div>
                      
                      {politicalTrades.purchases?.length > 0 && (
                        <div className="mb-3">
                          <div className="text-xs text-emerald-400 mb-2">📈 Purchases ({politicalTrades.purchases.length})</div>
                          {politicalTrades.purchases.slice(0, 5).map((pt, idx) => (
                            <div key={idx} className="text-sm text-slate-300 mb-1">
                              • {pt.politician} ({pt.party}) - {pt.trade_date} - {pt.amount_range}
                            </div>
                          ))}
                          {politicalTrades.purchases.length > 5 && (
                            <div className="text-xs text-slate-500 italic">+{politicalTrades.purchases.length - 5} more purchases</div>
                          )}
                        </div>
                      )}
                      
                      {politicalTrades.sales?.length > 0 && (
                        <div>
                          <div className="text-xs text-red-400 mb-2">📉 Sales ({politicalTrades.sales.length})</div>
                          {politicalTrades.sales.slice(0, 5).map((pt, idx) => (
                            <div key={idx} className="text-sm text-slate-300 mb-1">
                              • {pt.politician} ({pt.party}) - {pt.trade_date} - {pt.amount_range}
                            </div>
                          ))}
                          {politicalTrades.sales.length > 5 && (
                            <div className="text-xs text-slate-500 italic">+{politicalTrades.sales.length - 5} more sales</div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </>
              ) : (
                /* Insider Trade Details */
                <>
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
                </>
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
