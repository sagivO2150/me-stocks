import React from 'react';
import Tooltip from './Tooltip';

const LivePurchasesCard = ({ stock, onClick }) => {
  const ticker = stock.ticker;
  const companyName = stock.company_name;
  const totalValue = stock.total_value;
  const totalPurchases = stock.total_purchases;
  const uniqueInsiders = stock.unique_insiders;
  const cLevelCount = stock.c_level_count;
  const ownerCount = stock.owner_count;
  const clusterScore = stock.cluster_score;
  const priorityScore = stock.priority_score;
  
  // Format dollar values
  const formatValue = (value) => {
    if (value >= 1_000_000) {
      return `$${(value / 1_000_000).toFixed(2)}M`;
    } else if (value >= 1_000) {
      return `$${(value / 1_000).toFixed(0)}K`;
    }
    return `$${value.toFixed(0)}`;
  };

  // Get the largest purchase for display
  const largestPurchase = stock.purchases.reduce((max, p) => 
    p.value > max.value ? p : max, stock.purchases[0]);

  // Determine card color intensity based on priority score
  const getCardIntensity = () => {
    if (priorityScore >= 9) {
      return 'border-red-400 hover:border-red-300 hover:shadow-red-900/40 bg-red-950/30';
    } else if (priorityScore >= 7) {
      return 'border-orange-400 hover:border-orange-300 hover:shadow-orange-900/40 bg-orange-950/30';
    } else if (priorityScore >= 5) {
      return 'border-yellow-400 hover:border-yellow-300 hover:shadow-yellow-900/40 bg-yellow-950/30';
    }
    return 'border-slate-700 hover:border-blue-500 hover:shadow-blue-900/30 bg-slate-800/50';
  };

  // Get badge for shopping spree
  const isShoppingSpree = uniqueInsiders >= 2;
  const isCSuite = cLevelCount > 0;
  const isOwner = ownerCount > 0;

  return (
    <div 
      className={`border rounded-xl p-6 hover:shadow-2xl transition-all hover:scale-[1.02] cursor-pointer ${getCardIntensity()}`}
      onClick={onClick}
    >
      {/* Header: Ticker and Priority Score */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h2 className="text-3xl font-bold text-white">{ticker}</h2>
            {/* Priority Score Badge */}
            <Tooltip text="Priority Score: Combination of cluster activity (60%) and largest purchase size (40%). Higher = more significant.">
              <div className={`px-3 py-1 rounded-lg font-bold text-lg ${
                priorityScore >= 9 ? 'bg-red-500/30 text-red-300' :
                priorityScore >= 7 ? 'bg-orange-500/30 text-orange-300' :
                priorityScore >= 5 ? 'bg-yellow-500/30 text-yellow-300' :
                'bg-blue-500/30 text-blue-300'
              }`}>
                {priorityScore.toFixed(1)}
              </div>
            </Tooltip>
          </div>
          <p className="text-slate-400 text-sm mt-1">{companyName}</p>
        </div>
        
        {/* Total Value Badge */}
        <div className="flex flex-col items-end">
          <div className="text-emerald-400 font-bold text-2xl">{formatValue(totalValue)}</div>
          <div className="text-slate-500 text-xs">Total Today</div>
        </div>
      </div>

      {/* Key Signals Row */}
      <div className="flex flex-wrap gap-2 mb-4">
        {/* Shopping Spree Badge */}
        {isShoppingSpree && (
          <Tooltip text={`${uniqueInsiders} different insiders buying today = Shopping Spree! This is a strong bullish signal.`}>
            <span className="px-3 py-2 bg-red-500/30 text-red-300 rounded-lg text-sm font-bold animate-pulse">
              🛒 Shopping Spree ({uniqueInsiders})
            </span>
          </Tooltip>
        )}

        {/* C-Suite Badge */}
        {isCSuite && (
          <Tooltip text={`${cLevelCount} C-level executive(s) (CEO/CFO/COO/COB) buying today. Strong conviction signal.`}>
            <span className="px-3 py-2 bg-purple-500/30 text-purple-300 rounded-lg text-sm font-bold">
              👔 C-Suite ({cLevelCount})
            </span>
          </Tooltip>
        )}

        {/* 10% Owner Badge */}
        {isOwner && (
          <Tooltip text={`${ownerCount} major shareholder(s) (10%+ ownership) buying. Large stakeholders increasing positions.`}>
            <span className="px-3 py-2 bg-blue-500/30 text-blue-300 rounded-lg text-sm font-bold">
              🏢 10%+ Owner ({ownerCount})
            </span>
          </Tooltip>
        )}

        {/* Cluster Score */}
        <Tooltip text="Cluster Score: How much coordinated buying activity is happening. 8+ = strong cluster.">
          <span className={`px-3 py-2 rounded-lg text-sm font-medium ${
            clusterScore >= 8 ? 'bg-green-500/30 text-green-300' :
            clusterScore >= 5 ? 'bg-yellow-500/30 text-yellow-300' :
            'bg-slate-500/30 text-slate-300'
          }`}>
            📊 Cluster: {clusterScore}/10
          </span>
        </Tooltip>
      </div>

      {/* Largest Purchase Highlight */}
      {largestPurchase && (
        <div className="bg-slate-900/50 rounded-lg p-3 mb-3">
          <div className="text-slate-400 text-xs mb-1 font-semibold">LARGEST PURCHASE</div>
          <div className="flex justify-between items-center">
            <div>
              <div className="text-white font-medium">{largestPurchase.insider_name}</div>
              <div className="text-slate-400 text-sm">{largestPurchase.title}</div>
            </div>
            <div className="text-right">
              <div className="text-emerald-400 font-bold text-lg">
                {formatValue(largestPurchase.value)}
              </div>
              {largestPurchase.is_large && (
                <Tooltip text={`This purchase is in the top ${100 - largestPurchase.percentile}% of historical purchases for this stock.`}>
                  <div className="text-yellow-400 text-xs font-semibold">
                    {largestPurchase.percentile >= 95 ? '🔥 Top 5%' :
                     largestPurchase.percentile >= 90 ? '⭐ Top 10%' :
                     largestPurchase.percentile >= 75 ? '✨ Top 25%' : ''}
                  </div>
                </Tooltip>
              )}
            </div>
          </div>
        </div>
      )}

      {/* All Purchases Summary */}
      <div className="bg-slate-900/30 rounded-lg p-3">
        <div className="text-slate-400 text-xs mb-2 font-semibold">ALL PURCHASES TODAY</div>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <span className="text-slate-500">Total Transactions:</span>
            <span className="text-white font-medium ml-2">{totalPurchases}</span>
          </div>
          <div>
            <span className="text-slate-500">Unique Insiders:</span>
            <span className="text-white font-medium ml-2">{uniqueInsiders}</span>
          </div>
          <div>
            <span className="text-slate-500">Total Shares:</span>
            <span className="text-white font-medium ml-2">{stock.total_shares.toLocaleString()}</span>
          </div>
          <div>
            <span className="text-slate-500">Total Value:</span>
            <span className="text-white font-medium ml-2">{formatValue(totalValue)}</span>
          </div>
        </div>
      </div>

      {/* Purchase Details (collapsed, shown on hover or click) */}
      <div className="mt-3">
        <details className="text-xs text-slate-400">
          <summary className="cursor-pointer hover:text-slate-300">
            View all {totalPurchases} purchase{totalPurchases > 1 ? 's' : ''}
          </summary>
          <div className="mt-2 space-y-2 max-h-40 overflow-y-auto">
            {stock.purchases.map((purchase, idx) => (
              <div key={idx} className="bg-slate-800/50 rounded p-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-white font-medium">{purchase.insider_name}</span>
                  <span className="text-emerald-400 font-bold">{formatValue(purchase.value)}</span>
                </div>
                <div className="flex justify-between text-slate-500 mt-1">
                  <span>{purchase.role}</span>
                  <span>{purchase.shares.toLocaleString()} shares @ ${purchase.price}</span>
                </div>
                {purchase.is_large && (
                  <div className="text-yellow-400 text-xs mt-1">
                    ⭐ Top {100 - purchase.percentile}% purchase (Score: {purchase.score}/10)
                  </div>
                )}
              </div>
            ))}
          </div>
        </details>
      </div>
    </div>
  );
};

export default LivePurchasesCard;
