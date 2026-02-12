import React, { useState, useEffect } from 'react';
import Tooltip from './Tooltip';

const TopMonthlyCard = ({ stock }) => {
  const [eventBadge, setEventBadge] = useState(null);
  
  // Parse values
  const ticker = stock.ticker;
  const companyName = stock.company_name;
  const totalValue = stock.total_value_formatted;
  const totalPurchases = stock.total_purchases;
  const uniqueInsiders = stock.unique_insiders;
  const roleCounts = stock.role_counts || {};
  
  // Extract role counts
  const cobCount = roleCounts['COB'] || 0;
  const ceoCount = roleCounts['CEO'] || 0;
  const presCount = roleCounts['Pres'] || 0;
  const cfoCount = roleCounts['CFO'] || 0;
  const cooCount = roleCounts['COO'] || 0;
  const gcCount = roleCounts['GC'] || 0;
  const vpCount = roleCounts['VP'] || 0;
  const directorCount = roleCounts['Director'] || 0;
  const ownerCount = roleCounts['10% Owner'] || 0;
  const otherCount = roleCounts['Other'] || 0;

  // Build role breakdown text
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

  // Fetch event classification
  useEffect(() => {
    const fetchEventClassification = async () => {
      try {
        console.log(`🔍 [MONTHLY] Fetching event classification for ${ticker}`);
        const response = await fetch(`http://localhost:3001/api/event-classification/${ticker}`);
        console.log(`📡 [MONTHLY] Response status for ${ticker}:`, response.status);
        if (response.ok) {
          const data = await response.json();
          console.log(`📊 [MONTHLY] Event data for ${ticker}:`, data);
          if (data.success && data.primaryEvent) {
            console.log(`✅ [MONTHLY] Setting event badge for ${ticker}:`, data.primaryEvent);
            setEventBadge(data.primaryEvent);
          } else {
            console.log(`❌ [MONTHLY] No primary event for ${ticker}`);
          }
        } else {
          console.log(`⚠️ [MONTHLY] Failed to fetch events for ${ticker}:`, response.status);
        }
      } catch (err) {
        console.log(`❌ [MONTHLY] Error fetching events for ${ticker}:`, err);
      }
    };
    
    if (ticker) {
      console.log(`🎯 [MONTHLY] TopMonthlyCard for ${ticker} - will fetch events`);
      fetchEventClassification();
    }
  }, [ticker]);

  // Determine card intensity based on value and activity
  const getCardIntensity = () => {
    if (stock.total_value >= 10_000_000) return 'border-emerald-400 hover:border-emerald-300 hover:shadow-emerald-900/30';
    if (stock.total_value >= 5_000_000) return 'border-blue-400 hover:border-blue-300 hover:shadow-blue-900/30';
    if (stock.total_value >= 1_000_000) return 'border-yellow-400 hover:border-yellow-300 hover:shadow-yellow-900/30';
    return 'border-slate-700 hover:border-blue-500 hover:shadow-blue-900/30';
  };

  return (
    <div className={`bg-slate-800/50 border rounded-xl p-6 hover:shadow-2xl transition-all hover:scale-[1.02] cursor-pointer ${getCardIntensity()}`}>
      {/* Header: Ticker */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <h2 className="text-3xl font-bold text-white">{ticker}</h2>
          <p className="text-slate-400 text-sm mt-1">{companyName}</p>
        </div>
        
        {/* Total Value Badge */}
        <div className="flex flex-col items-end">
          <div className="text-emerald-400 font-bold text-2xl">{totalValue}</div>
          <div className="text-slate-500 text-xs">Monthly Volume</div>
        </div>
      </div>

      {/* Badges Row - Event Classification Only */}
      <div className="flex flex-wrap gap-2 mb-4">
        {/* Event Classification Badge */}
        {eventBadge ? (
          <Tooltip text={eventBadge.tooltip}>
            <span className={`px-3 py-2 rounded-lg text-sm font-medium ${eventBadge.colorClass}`}>
              {eventBadge.icon} {eventBadge.label}
            </span>
          </Tooltip>
        ) : (
          <span className="px-3 py-2 bg-slate-700/30 text-slate-500 rounded-lg text-sm font-medium">
            ⏳ Analyzing...
          </span>
        )}
      </div>

      {/* Role Breakdown Section */}
      <div className="bg-slate-900/50 rounded-lg p-3 mb-4">
        <div className="text-slate-400 text-xs mb-2 font-semibold">INSIDER BREAKDOWN</div>
        <div className="text-slate-200 text-sm">{roleBreakdownText}</div>
      </div>

      {/* Key Stats Grid */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-slate-900/30 rounded-lg p-3">
          <div className="text-slate-500 text-xs mb-1">Avg per Trade</div>
          <div className="text-white font-semibold">
            {(() => {
              const avgValue = stock.total_value / totalPurchases;
              if (avgValue >= 1_000_000_000) {
                return `$${(avgValue / 1_000_000_000).toFixed(2)}B`;
              } else if (avgValue >= 1_000_000) {
                return `$${(avgValue / 1_000_000).toFixed(1)}M`;
              } else if (avgValue >= 1_000) {
                return `$${(avgValue / 1_000).toFixed(0)}K`;
              } else {
                return `$${avgValue.toFixed(0)}`;
              }
            })()}
          </div>
        </div>
        
        <div className="bg-slate-900/30 rounded-lg p-3">
          <div className="text-slate-500 text-xs mb-1">C-Level/Directors</div>
          <div className="text-white font-semibold">
            {cobCount + ceoCount + presCount + cfoCount + cooCount + gcCount + directorCount}
          </div>
          <div className="text-slate-500 text-xs mt-1">10%ers/Other</div>
          <div className="text-white font-semibold text-sm">
            {ownerCount + otherCount}
          </div>
        </div>
      </div>

      {/* Recent Trades Preview */}
      {stock.trades && stock.trades.length > 0 && (
        <div className="mt-4 pt-4 border-t border-slate-700">
          <div className="text-slate-400 text-xs mb-2">RECENT ACTIVITY</div>
          {stock.trades.slice(0, 3).map((trade, idx) => (
            <div key={idx} className="text-xs text-slate-300 mb-1 flex justify-between">
              <span className="truncate flex-1">{trade.insider_name} ({trade.role})</span>
              <span className="text-emerald-400 ml-2">{trade.value}</span>
            </div>
          ))}
          {stock.trades.length > 3 && (
            <div className="text-xs text-slate-500 italic mt-1">
              +{stock.trades.length - 3} more trades...
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TopMonthlyCard;
