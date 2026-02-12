import React from 'react';
import Tooltip from './Tooltip';

const TopMonthlyCard = ({ stock }) => {
  // Parse values
  const ticker = stock.ticker;
  const companyName = stock.company_name;
  const totalValue = stock.total_value_formatted;
  const totalPurchases = stock.total_purchases;
  const uniqueInsiders = stock.unique_insiders;
  const roleCounts = stock.role_counts || {};
  
  // Handle both old (object) and new (array) eventClassification formats
  let events = [];
  if (Array.isArray(stock.eventClassification)) {
    events = stock.eventClassification;
  } else if (stock.eventClassification && typeof stock.eventClassification === 'object') {
    // Old format - convert single event to array
    events = [{ type: 'clamp', count: 1 }]; // Fallback
  }
  
  // Event badge config
  const eventLabels = {
    'holy-grail': { label: 'Holy Grail', icon: '🔥', colorClass: 'bg-purple-500/20 text-purple-400 border-purple-500/30', tooltip: 'Clamp + price up!' },
    'slump-recovery': { label: 'Slump Recovery', icon: '📈', colorClass: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', tooltip: 'Bottom-fishing success!' },
    'clamp': { label: 'Clamp', icon: '📊', colorClass: 'bg-blue-500/20 text-blue-400 border-blue-500/30', tooltip: 'Purchases within 7 days' },
    'restock': { label: 'Restock', icon: '🔄', colorClass: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30', tooltip: '3+ purchases in 30 days' },
    'plateau': { label: 'Plateau', icon: '📊', colorClass: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30', tooltip: 'Stable buy with follow-up' },
    'mid-rise': { label: 'Mid-Rise', icon: '⚠️', colorClass: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30', tooltip: 'Buying during uptrend' },
    'disqualified': { label: 'Disqualified', icon: '❌', colorClass: 'bg-red-500/20 text-red-400 border-red-500/30', tooltip: "Didn't work out" }
  };
  
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

      {/* Badges Row - All Event Classifications */}
      <div className="flex flex-wrap gap-2 mb-4">
        {events.map((event, idx) => {
          const config = eventLabels[event.type];
          if (!config) return null;
          
          const displayLabel = event.count > 1 ? `${event.count} ${config.label}` : config.label;
          
          return (
            <Tooltip key={`${event.type}-${idx}`} text={config.tooltip}>
              <span className={`px-3 py-2 rounded-lg text-sm font-medium border ${config.colorClass}`}>
                {config.icon} {displayLabel}
              </span>
            </Tooltip>
          );
        })}
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
