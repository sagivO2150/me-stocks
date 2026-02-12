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
      // Check if we need to fetch data
      if (!stockHistory?.history) {
        // No data yet, fetch MAX
        console.log('No stock history yet, fetching MAX to cover focus date');
        fetchStockHistory('max');
        return;
      }
      
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
      
      // Focus date is within range - don't fetch new data, just let the filter work
      console.log('Focus date within range, using existing data with period filter');
      return;
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

  // Classify insider trading events into strategic categories
  const classifyInsiderEvents = () => {
    console.log('🔍 classifyInsiderEvents called');
    console.log('stockHistory:', stockHistory);
    console.log('insiderTrades:', insiderTrades);
    
    if (!stockHistory || !stockHistory.history || !insiderTrades || !insiderTrades.purchases) {
      console.log('❌ Missing data:', {
        hasStockHistory: !!stockHistory,
        hasHistory: !!(stockHistory?.history),
        hasInsiderTrades: !!insiderTrades,
        hasPurchases: !!(insiderTrades?.purchases)
      });
      return { events: [], disqualifiedCount: 0 };
    }

    console.log('✅ Has all required data, processing...');
    const events = [];
    const disqualifiedEvents = [];
    const purchases = insiderTrades.purchases;
    console.log(`Processing ${purchases.length} purchases`);
    
    // Group purchases by date
    const purchasesByDate = {};
    purchases.forEach(trade => {
      const dateKey = trade.date.split('T')[0];
      if (!purchasesByDate[dateKey]) {
        purchasesByDate[dateKey] = [];
      }
      purchasesByDate[dateKey].push(trade);
    });

    // Get sorted dates
    const sortedDates = Object.keys(purchasesByDate).sort();
    
    // Identify clamps (2+ consecutive days of purchases, ends with 7+ days gap)
    const clamps = [];
    let currentClamp = null;
    
    for (let i = 0; i < sortedDates.length; i++) {
      const currentDate = new Date(sortedDates[i]);
      const nextDate = i < sortedDates.length - 1 ? new Date(sortedDates[i + 1]) : null;
      
      if (!currentClamp) {
        currentClamp = {
          startDate: sortedDates[i],
          endDate: sortedDates[i],
          dates: [sortedDates[i]],
          totalValue: 0,
          purchaseCount: 0
        };
      } else {
        currentClamp.endDate = sortedDates[i];
        currentClamp.dates.push(sortedDates[i]);
      }
      
      // Add purchase data
      purchasesByDate[sortedDates[i]].forEach(trade => {
        currentClamp.totalValue += trade.value;
        currentClamp.purchaseCount++;
      });
      
      // Check if next date breaks the clamp (7+ days gap)
      if (nextDate) {
        const daysDiff = (nextDate - currentDate) / (1000 * 60 * 60 * 24);
        if (daysDiff > 7) {
          // Save clamp if it has 2+ days
          if (currentClamp.dates.length >= 2) {
            clamps.push(currentClamp);
          }
          currentClamp = null;
        }
      } else {
        // Last date - save clamp if it has 2+ days
        if (currentClamp && currentClamp.dates.length >= 2) {
          clamps.push(currentClamp);
        }
      }
    }

    // Create a map of dates that are part of clamps
    const clampDates = new Set();
    clamps.forEach(clamp => {
      clamp.dates.forEach(date => clampDates.add(date));
    });

    // Get stock price data indexed by date
    const priceByDate = {};
    stockHistory.history.forEach(point => {
      const dateKey = point.date.split('T')[0].split(' ')[0];
      if (!priceByDate[dateKey]) {
        priceByDate[dateKey] = parseFloat(point.close);
      }
    });

    // Helper: Get price at date
    const getPriceAt = (dateStr) => {
      return priceByDate[dateStr];
    };

    // Helper: Get price N days before/after
    const getPriceOffset = (dateStr, dayOffset) => {
      const date = new Date(dateStr);
      date.setDate(date.getDate() + dayOffset);
      let checkDate = date.toISOString().split('T')[0];
      
      // Try to find nearest price within 3 days
      for (let i = 0; i < 3; i++) {
        if (priceByDate[checkDate]) return priceByDate[checkDate];
        date.setDate(date.getDate() + (dayOffset > 0 ? 1 : -1));
        checkDate = date.toISOString().split('T')[0];
      }
      return null;
    };

    // Helper: Check if stock was in slump (trending down for ~30 days before)
    const wasInSlump = (dateStr) => {
      const price = getPriceAt(dateStr);
      const price30DaysBefore = getPriceOffset(dateStr, -30);
      if (!price || !price30DaysBefore) return false;
      return price30DaysBefore > price * 1.15; // Stock was 15%+ higher 30 days ago
    };

    // Helper: Check if stock went up after trade
    const wentUpAfterTrade = (dateStr, minPercent = 10) => {
      const priceAtTrade = getPriceAt(dateStr);
      const price3DaysAfter = getPriceOffset(dateStr, 3);
      if (!priceAtTrade || !price3DaysAfter) return false;
      const percentChange = ((price3DaysAfter - priceAtTrade) / priceAtTrade) * 100;
      return percentChange >= minPercent;
    };

    // Helper: Check if stock was rising before trade
    const wasRising = (dateStr) => {
      const price = getPriceAt(dateStr);
      const price7DaysBefore = getPriceOffset(dateStr, -7);
      if (!price || !price7DaysBefore) return false;
      return price > price7DaysBefore * 1.05; // Stock was up 5%+ in past week
    };

    // Classify each clamp
    clamps.forEach(clamp => {
      const inSlump = wasInSlump(clamp.startDate);
      const wentUp = wentUpAfterTrade(clamp.endDate, 10);
      
      // Check if this is a restock (within 1 month of previous clamp)
      const isRestock = clamps.some(prevClamp => {
        if (prevClamp === clamp) return false;
        const prevEnd = new Date(prevClamp.endDate);
        const currentStart = new Date(clamp.startDate);
        const daysDiff = (currentStart - prevEnd) / (1000 * 60 * 60 * 24);
        return daysDiff > 0 && daysDiff <= 30;
      });

      if (isRestock) {
        events.push({
          type: 'restock',
          date: clamp.startDate,
          endDate: clamp.endDate,
          description: `Restock Event - Continued buying (${clamp.dates.length} days)`,
          value: clamp.totalValue,
          purchaseCount: clamp.purchaseCount
        });
      } else if (inSlump && wentUp) {
        events.push({
          type: 'slump',
          date: clamp.startDate,
          endDate: clamp.endDate,
          description: `Slump Recovery - Bottom fishing (${clamp.dates.length} days)`,
          value: clamp.totalValue,
          purchaseCount: clamp.purchaseCount
        });
      } else if (wentUp) {
        events.push({
          type: 'clamp',
          date: clamp.startDate,
          endDate: clamp.endDate,
          description: `Holy Grail Clamp - Shopping spree (${clamp.dates.length} days)`,
          value: clamp.totalValue,
          purchaseCount: clamp.purchaseCount
        });
      }
    });

    // Process singular trades (not part of clamps)
    sortedDates.forEach(date => {
      if (clampDates.has(date)) return; // Skip clamp dates

      const trades = purchasesByDate[date];
      const totalValue = trades.reduce((sum, t) => sum + t.value, 0);
      const rising = wasRising(date);
      const wentUp = wentUpAfterTrade(date, 10);

      if (rising && !wentUp) {
        // Mid-rise event (stock was rising, insider bought, then crashed)
        events.push({
          type: 'mid-rise',
          date: date,
          description: 'Mid-Rise - Bought on the way up (crashed after)',
          value: totalValue,
          purchaseCount: trades.length
        });
      } else if (!wentUp) {
        // Disqualified - stock didn't go up after singular purchase
        disqualifiedEvents.push({
          date: date,
          value: totalValue,
          purchaseCount: trades.length
        });
      }
    });

    const result = { 
      events: events.sort((a, b) => new Date(b.date) - new Date(a.date)),
      disqualifiedCount: disqualifiedEvents.length 
    };
    
    console.log('📊 Event classification result:', result);
    console.log(`Found ${result.events.length} events, ${result.disqualifiedCount} disqualified`);
    
    return result;
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

  // Format date to DD-MM-YYYY format
  const formatDate = (dateString) => {
    // Extract date part (YYYY-MM-DD) from dateString which might include time
    const datePart = dateString.split('T')[0].split(' ')[0];
    const [year, month, day] = datePart.split('-');
    return `${day}-${month}-${year}`;
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
            <p className="text-slate-300 text-sm font-semibold mb-2">{formatDate(data.date)}</p>
            <p className="text-xs text-blue-300 mb-2">📊 Stock Price: ${data.close ? data.close.toFixed(2) : 'N/A'}</p>
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
      
      return (
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-xl max-h-96 overflow-y-auto">
          <p className="text-slate-300 text-sm font-semibold mb-1 sticky top-0 bg-slate-800">{formatDate(data.date)}</p>
          <p className="text-xs text-blue-300 mb-2">📊 Stock Price: ${data.close ? data.close.toFixed(2) : 'N/A'}</p>
          
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

  // Event badge config for display
  const eventLabels = {
    'bottom-fishing-win': { label: 'Bottom Catch', icon: '🎯', colorClass: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', tooltip: 'Bought after heavy drawdown and rebounded.' },
    'breakout-accumulation': { label: 'Breakout Build', icon: '🚀', colorClass: 'bg-purple-500/20 text-purple-400 border-purple-500/30', tooltip: 'Accumulation cluster followed by a breakout.' },
    'slow-burn-accumulation': { label: 'Slow Burn', icon: '🟢', colorClass: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30', tooltip: 'Improved more gradually over ~20 days.' },
    'stabilizing-accumulation': { label: 'Stabilizing', icon: '🧱', colorClass: 'bg-blue-500/20 text-blue-400 border-blue-500/30', tooltip: 'Insider buying likely provided support.' },
    'needs-follow-through': { label: 'Pending', icon: '⏳', colorClass: 'bg-slate-500/20 text-slate-300 border-slate-500/30', tooltip: 'Too recent to score confidently.' },
    'late-chase': { label: 'Late Chase', icon: '⚠️', colorClass: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30', tooltip: 'Bought into an uptrend, then momentum weakened.' },
    'failed-support': { label: 'Failed Support', icon: '❌', colorClass: 'bg-red-500/20 text-red-400 border-red-500/30', tooltip: 'Buying failed to hold the line.' },
    // Legacy aliases for existing JSON files
    'holy-grail': { label: 'Breakout Build', icon: '🚀', colorClass: 'bg-purple-500/20 text-purple-400 border-purple-500/30', tooltip: 'Legacy: strong post-buy breakout.' },
    'slump-recovery': { label: 'Bottom Catch', icon: '🎯', colorClass: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', tooltip: 'Legacy: rebound from slump.' },
    'clamp': { label: 'Pending', icon: '⏳', colorClass: 'bg-slate-500/20 text-slate-300 border-slate-500/30', tooltip: 'Legacy: clustered buys pending outcome.' },
    'restock': { label: 'Slow Burn', icon: '🟢', colorClass: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30', tooltip: 'Legacy: repeated accumulation.' },
    'plateau': { label: 'Stabilizing', icon: '🧱', colorClass: 'bg-blue-500/20 text-blue-400 border-blue-500/30', tooltip: 'Legacy: neutral accumulation.' },
    'mid-rise': { label: 'Late Chase', icon: '⚠️', colorClass: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30', tooltip: 'Legacy: bought during run-up.' },
    'disqualified': { label: 'Failed Support', icon: '❌', colorClass: 'bg-red-500/20 text-red-400 border-red-500/30', tooltip: 'Legacy: trade had poor follow-through.' }
  };

  // Get event classification from trade if available
  const events = Array.isArray(trade.eventClassification) ? trade.eventClassification : [];
  
  // State for tracking which badge dropdown is open
  const [expandedBadge, setExpandedBadge] = useState(null);
  
  // State for tracking hovered campaign dates in dropdown (to highlight on chart)
  const [hoveredCampaignDates, setHoveredCampaignDates] = useState([]);
  
  // Debug: log events to see if dates are present
  console.log('Events for', ticker, ':', events);

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-6xl w-full h-[90vh] flex flex-col shadow-2xl" style={{outline: 'none'}}>
        {/* Header */}
        <div className="bg-slate-900 border-b border-slate-700 p-6 flex justify-between items-start flex-shrink-0">
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
            
            {/* Event Classification Badges */}
            {events.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {events.map((event, idx) => {
                  const config = eventLabels[event.type];
                  if (!config) return null;
                  
                  const displayLabel = event.count > 1 ? `${event.count} ${config.label}` : config.label;
                  const isExpanded = expandedBadge === `${event.type}-${idx}`;
                  const hasDates = event.dates && event.dates.length > 0;
                  
                  return (
                    <div 
                      key={`${event.type}-${idx}`} 
                      className="relative"
                      onMouseEnter={() => hasDates && setExpandedBadge(`${event.type}-${idx}`)}
                      onMouseLeave={() => setExpandedBadge(null)}
                    >
                      <button
                        className={`px-2 py-1 rounded-lg text-xs font-medium border ${config.colorClass} cursor-pointer hover:opacity-80 transition-opacity`}
                        title={config.tooltip}
                      >
                        {config.icon} {displayLabel} {hasDates && (isExpanded ? '▲' : '▼')}
                      </button>
                      
                      {/* Dropdown with dates */}
                      {isExpanded && hasDates && (
                        <div className="absolute top-full left-0 bg-slate-800 border border-slate-600 rounded-lg shadow-xl z-10 min-w-[150px]">
                          <div className="p-2 pt-3 text-xs text-slate-300">
                            {event.dates.map((date, dateIdx) => {
                              // Get all campaign dates for this date
                              const campaignInfo = event.campaigns ? event.campaigns[dateIdx] : null;
                              const allCampaignDates = campaignInfo?.allDates || [date];
                              
                              return (
                                <button
                                  key={dateIdx}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setFocusDate(date);
                                    setExpandedBadge(null); // Close dropdown after selecting
                                  }}
                                  onMouseEnter={() => setHoveredCampaignDates(allCampaignDates)}
                                  onMouseLeave={() => setHoveredCampaignDates([])}
                                  className="w-full text-left py-1 px-2 hover:bg-slate-700 rounded cursor-pointer transition-colors"
                                >
                                  📅 {new Date(date).toLocaleDateString('en-US', { 
                                    month: 'short', 
                                    day: 'numeric', 
                                    year: 'numeric' 
                                  })} {allCampaignDates.length > 1 && `(${allCampaignDates.length} trades)`}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
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

        {/* Content - scrollable area */}
        <div className="p-6 overflow-y-auto flex-1">
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
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                      edgarLoading
                        ? 'bg-slate-700 text-slate-500 cursor-wait'
                        : 'bg-green-600 text-white hover:bg-green-500'
                    }`}
                  >
                    {edgarLoading ? (
                      <>
                        <span className="inline-block animate-spin mr-1.5 text-sm">⏳</span>
                        <span className="text-sm">Loading EDGAR...</span>
                      </>
                    ) : (
                      <>
                        📈 5yr EDGAR History
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
                        
                        // Check if this date matches any of the hovered campaign dates
                        const payloadDate = payload.date ? payload.date.split('T')[0] : null;
                        const isHovered = hoveredCampaignDates.some(campaignDate => 
                          campaignDate && payloadDate && campaignDate.split('T')[0] === payloadDate
                        );
                        
                        // Render multiple dots if there are multiple trades
                        const trades = payload.purchaseTrades;
                        const numTrades = trades.length;
                        
                        if (numTrades === 1) {
                          // Single trade - one dot (enlarged if hovered)
                          return (
                            <circle 
                              key={`purchase-${cx}-${cy}`} 
                              cx={cx} 
                              cy={cy} 
                              r={isHovered ? 14 : 8} 
                              fill="#10b981" 
                              stroke={isHovered ? "#fbbf24" : "#fff"} 
                              strokeWidth={isHovered ? 4 : 2}
                              className={isHovered ? "animate-pulse" : ""}
                            />
                          );
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
                                  r={isHovered ? 10 : 7}
                                  fill="#10b981"
                                  stroke={isHovered ? "#fbbf24" : "#fff"}
                                  strokeWidth={isHovered ? 3 : 2}
                                  className={isHovered ? "animate-pulse" : ""}
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
        </div>
      </div>
    </div>
  );
};

export default StockDetail;
