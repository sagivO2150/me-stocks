import React from 'react';
import Tooltip from './Tooltip';

function PoliticalTradeCard({ trade }) {
  // Parse political trade data
  const politician = trade.politician || 'Unknown';
  const ticker = trade.ticker || 'N/A';
  const assetDescription = trade.asset_description || '';
  const tradeType = trade.trade_type || 'Unknown';
  const tradeDate = trade.trade_date || '';
  const amountRange = trade.amount_range || '';
  const amountValue = parseFloat(trade.amount_value) || 0;
  const party = trade.party || '';
  const source = trade.source || 'Congress';
  const state = trade.state || '';
  const district = trade.district || '';
  const committee = trade.committee || '';

  // Format amount for display
  const formatAmount = (value) => {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`;
    } else if (value >= 1000) {
      return `$${(value / 1000).toFixed(0)}K`;
    }
    return `$${value}`;
  };

  // Party color
  const partyColor = party === 'Democrat' ? 'text-blue-400' : 
                     party === 'Republican' ? 'text-red-400' : 
                     'text-gray-400';
  
  const partyBorder = party === 'Democrat' ? 'border-blue-500/30' : 
                      party === 'Republican' ? 'border-red-500/30' : 
                      'border-gray-500/30';

  // Trade type styling
  const isPurchase = tradeType === 'Purchase';
  const tradeColor = isPurchase ? 'text-emerald-400' : 'text-red-400';
  const tradeBg = isPurchase ? 'bg-emerald-500/10' : 'bg-red-500/10';
  const tradeIcon = isPurchase ? '📈' : '📉';

  // Source badge
  const sourceBadge = source === 'Senate' ? '🏛️ Senate' : '🏛️ House';

  return (
    <div className={`bg-slate-800 rounded-lg p-6 border-2 ${partyBorder} hover:border-blue-400 transition cursor-pointer shadow-lg hover:shadow-blue-500/20`}>
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <h3 className={`text-2xl font-bold ${partyColor}`}>
              {politician}
            </h3>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs bg-slate-700 px-2 py-1 rounded">
              {sourceBadge}
            </span>
            {party && (
              <span className={`text-xs ${partyColor} bg-slate-700 px-2 py-1 rounded`}>
                {party}
              </span>
            )}
            {state && (
              <span className="text-xs text-slate-400 bg-slate-700 px-2 py-1 rounded">
                {state}{district && `-${district}`}
              </span>
            )}
            {committee && (
              <span className="text-xs text-yellow-400 bg-slate-700 px-2 py-1 rounded">
                📋 {committee}
              </span>
            )}
          </div>
        </div>
        
        <div className={`${tradeBg} px-4 py-2 rounded-lg`}>
          <div className="text-center">
            <div className="text-xs text-slate-400 mb-1">Trade Type</div>
            <div className={`font-bold ${tradeColor}`}>
              {tradeIcon} {tradeType}
            </div>
          </div>
        </div>
      </div>

      {/* Ticker & Asset */}
      <div className="mb-4 bg-slate-700/30 rounded-lg p-4">
        <div className="flex items-baseline gap-3">
          <span className="text-3xl font-bold text-white">{ticker}</span>
          {assetDescription && (
            <span className="text-sm text-slate-400">{assetDescription}</span>
          )}
        </div>
      </div>

      {/* Trade Details Grid */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Amount */}
        <div className="bg-slate-700/30 rounded-lg p-3">
          <Tooltip text="Estimated value of the trade based on disclosed range. Congressional trades are reported in ranges, this shows the midpoint.">
            <div className="text-xs text-slate-400 mb-1 border-b border-dotted border-slate-600 inline-block">
              Est. Value
            </div>
          </Tooltip>
          <div className="text-xl font-bold text-yellow-400">
            {formatAmount(amountValue)}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {amountRange}
          </div>
        </div>

        {/* Trade Date */}
        <div className="bg-slate-700/30 rounded-lg p-3">
          <div className="text-xs text-slate-400 mb-1">Trade Date</div>
          <div className="text-lg font-bold text-slate-200">
            {tradeDate}
          </div>
        </div>
      </div>

      {/* Signal Strength Indicator */}
      <div className="mt-4 pt-4 border-t border-slate-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Tooltip text="Political trades can signal upcoming policy changes or insider knowledge of regulatory shifts.">
              <span className="text-xs text-slate-400 border-b border-dotted border-slate-500">
                🎯 Political Signal
              </span>
            </Tooltip>
          </div>
          <div className="flex items-center gap-2">
            {committee && (
              <Tooltip text={`${politician} serves on the ${committee} committee, potentially relevant to ${ticker}`}>
                <div className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-1 rounded border border-yellow-500/30">
                  ⚠️ Committee Relevance
                </div>
              </Tooltip>
            )}
            {amountValue >= 1000000 && (
              <Tooltip text="Large trade value indicates high conviction">
                <div className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-1 rounded border border-emerald-500/30">
                  💰 High Value
                </div>
              </Tooltip>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default PoliticalTradeCard;
