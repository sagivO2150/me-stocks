import React from 'react';

const TradeCard = ({ trade }) => {
  // Parse values
  const ticker = trade.Ticker;
  const insidersCount = parseInt(trade.Insiders) || 0;
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
  const betaClass = trade.Beta_Classification;
  const whaleStatus = trade.Whale_Status;
  const scoreReasons = trade.Score_Reasons;

  // Calculate discount/upside
  let upside = 'N/A';
  if (targetMeanPrice && currentPrice && !isNaN(targetMeanPrice) && !isNaN(currentPrice)) {
    const discountPct = ((targetMeanPrice - currentPrice) / currentPrice) * 100;
    upside = discountPct > 0 ? `+${discountPct.toFixed(1)}%` : `${discountPct.toFixed(1)}%`;
  }

  // Score color
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

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 hover:border-slate-600 transition-all hover:shadow-xl hover:shadow-slate-900/50">
      {/* Header: Ticker */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-3xl font-bold text-white">{ticker}</h2>
          <p className="text-slate-400 text-sm mt-1">{sector || 'Unknown Sector'}</p>
        </div>
        
        {/* Rainy Day Score Circle */}
        <div className={`flex flex-col items-center justify-center w-20 h-20 rounded-full border-4 ${getScoreColor(rainyDayScore)} ${getScoreBg(rainyDayScore)}`}>
          <div className={`text-2xl font-bold ${getScoreColor(rainyDayScore)}`}>
            {rainyDayScore}
          </div>
          <div className="text-xs text-slate-400">/ 10</div>
        </div>
      </div>

      {/* Badges Row */}
      <div className="flex flex-wrap gap-2 mb-4">
        {/* Insiders Count */}
        <span className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-full text-sm font-medium border border-blue-500/30">
          👥 {insidersCount} Insiders
        </span>

        {/* Conviction Badge */}
        {skinInGame === 'YES' ? (
          <span className="px-3 py-1 bg-emerald-500/20 text-emerald-400 rounded-full text-sm font-medium border border-emerald-500/30">
            💎 HIGH CONVICTION
          </span>
        ) : (
          <span className="px-3 py-1 bg-slate-700/50 text-slate-400 rounded-full text-sm font-medium border border-slate-600">
            Low Conviction
          </span>
        )}
      </div>

      {/* Trade Info */}
      <div className="space-y-3 mb-4">
        <div className="flex justify-between items-center">
          <span className="text-slate-400 text-sm">Trade Value</span>
          <span className="text-white font-semibold">{value}</span>
        </div>
        
        <div className="flex justify-between items-center">
          <span className="text-slate-400 text-sm">Ownership Change</span>
          <span className="text-emerald-400 font-semibold">{deltaOwn}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-slate-400 text-sm">Trade Date</span>
          <span className="text-white text-sm">{tradeDate}</span>
        </div>

        {/* Upside */}
        {upside !== 'N/A' && (
          <div className="flex justify-between items-center pt-2 border-t border-slate-700">
            <span className="text-slate-400 text-sm">Upside to Target</span>
            <span className={`font-bold text-lg ${upside.startsWith('+') ? 'text-emerald-400' : 'text-red-400'}`}>
              {upside}
            </span>
          </div>
        )}
      </div>

      {/* Health Flags */}
      {healthFlags && healthFlags !== 'N/A' && (
        <div className="bg-slate-900/50 rounded-lg p-3 mb-3">
          <div className="text-xs text-slate-400 mb-1">Financial Health</div>
          <div className="text-sm text-slate-200">{healthFlags}</div>
        </div>
      )}

      {/* Sector Type Badge */}
      {sectorType && (
        <div className="mt-3">
          {sectorType.includes('DEFENSIVE') && (
            <div className="bg-green-500/10 border border-green-500/30 rounded-lg px-3 py-2">
              <div className="text-green-400 text-xs font-semibold">🛡️ {sectorType}</div>
            </div>
          )}
          {sectorType.includes('AGGRESSIVE') && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
              <div className="text-red-400 text-xs font-semibold">⚠️ {sectorType}</div>
            </div>
          )}
          {sectorType.includes('NEUTRAL') && (
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg px-3 py-2">
              <div className="text-blue-400 text-xs font-semibold">⚖️ {sectorType}</div>
            </div>
          )}
        </div>
      )}

      {/* Score Reasons */}
      {scoreReasons && scoreReasons !== 'N/A' && (
        <div className="mt-3 text-xs text-slate-400">
          <span className="font-semibold">Score Factors:</span> {scoreReasons}
        </div>
      )}
    </div>
  );
};

export default TradeCard;
