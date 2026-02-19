import React, { useState, useEffect } from 'react';
import Tooltip from './Tooltip';

const TradeCard = ({ trade }) => {
  const [eventBadge, setEventBadge] = useState(null);
  const [reputation, setReputation] = useState(null);
  
  // Parse values
  const ticker = trade.Ticker;
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
  const tradeType = trade.Trade_Type || '';
  const isSale = tradeType.includes('Sale') || tradeType.includes('S -');
  
  // For sales, Delta_Own should be displayed as negative
  let deltaOwn = trade.Delta_Own;
  if (isSale && deltaOwn && !deltaOwn.startsWith('-')) {
    deltaOwn = '-' + deltaOwn.replace('+', '');
  }
  
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

  // Build role breakdown text (no count for singular C-suite roles)
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
        const response = await fetch(`http://localhost:3001/api/event-classification/${ticker}`);
        if (response.ok) {
          const data = await response.json();
          if (data.success && data.primaryEvent) {
            setEventBadge(data.primaryEvent);
          }
        }
      } catch (err) {
        // Silently fail - events are optional enhancement
      }
    };
    
    if (ticker && !isSale) { // Only for purchases
      fetchEventClassification();
    }
  }, [ticker, isSale]);

  // Fetch reputation score
  useEffect(() => {
    const fetchReputation = async () => {
      try {
        const response = await fetch(`http://localhost:3001/api/reputation-scores`);
        if (response.ok) {
          const data = await response.json();
          if (data.success && data.scores) {
            const tickerRep = data.scores.find(s => s.ticker === ticker);
            if (tickerRep) {
              setReputation(tickerRep);
            }
          }
        }
      } catch (err) {
        // Silently fail - reputation is optional
      }
    };
    
    if (ticker && !isSale) {
      fetchReputation();
    }
  }, [ticker, isSale]);

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
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 hover:border-blue-500 hover:shadow-2xl hover:shadow-blue-900/30 transition-all hover:scale-[1.02] cursor-pointer">
      {/* Header: Ticker */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-3xl font-bold text-white">{ticker}</h2>
          <p className="text-slate-400 text-sm mt-1">{sector || 'Unknown Sector'}</p>
        </div>
        
        {/* Rainy Day Score Circle */}
        <Tooltip text="Overall conviction score (0-10). Based on: insider clustering (3+ = good), high transaction value, ownership increase %, financial health, and sector defensive strength. 8+ = strong buy signal, 6-7 = solid, 4-5 = cautious, <4 = speculative.">
          <div className={`flex flex-col items-center justify-center w-20 h-20 rounded-full border-4 ${getScoreColor(rainyDayScore)} ${getScoreBg(rainyDayScore)}`}>
            <div className={`text-2xl font-bold ${getScoreColor(rainyDayScore)}`}>
              {rainyDayScore}
            </div>
            <div className="text-xs text-slate-400">/ 10</div>
          </div>
        </Tooltip>
      </div>

      {/* Badges Row */}
      <div className="flex flex-wrap gap-2 mb-4">
        {/* Reputation Badge */}
        {reputation && (
          <Tooltip text={`Track Record: ${reputation.total_purchases} insider purchases tracked. Average gain: ${parseFloat(reputation.avg_gain).toFixed(1)}%. Score: ${parseFloat(reputation.avg_score).toFixed(2)}. ${reputation.category === 'excellent' ? 'Insiders have excellent timing - relaxed stop loss (-2.5%), larger positions (1.5x).' : reputation.category === 'good' ? 'Insiders show good timing - slightly relaxed stop loss (-3.5%), larger positions (1.25x).' : reputation.category === 'neutral' ? 'Average track record - standard parameters.' : 'Poor track record - tighter stop loss (-7.5%), smaller positions (0.75x).'}`}>
            <span className={`px-3 py-1 rounded-full text-sm font-medium border ${
              reputation.category === 'excellent' ? 'bg-purple-500/20 text-purple-400 border-purple-500/30' :
              reputation.category === 'good' ? 'bg-green-500/20 text-green-400 border-green-500/30' :
              reputation.category === 'poor' ? 'bg-red-500/20 text-red-400 border-red-500/30' :
              'bg-slate-700/50 text-slate-400 border-slate-600'
            }`}>
              {reputation.category === 'excellent' ? '⭐ EXCELLENT' :
               reputation.category === 'good' ? '👍 GOOD' :
               reputation.category === 'poor' ? '⚠️ POOR' :
               '➖ NEUTRAL'} TRACK RECORD
            </span>
          </Tooltip>
        )}

        {/* Insiders Count with Role Breakdown */}
        <Tooltip text={isSale
          ? `Number of insiders selling this stock. Breakdown: ${roleBreakdownText}. Cluster selling (3+) can signal concerns about company outlook, though sales often happen for benign reasons (diversification, liquidity needs).`
          : `Number of insiders buying this stock. Breakdown: ${roleBreakdownText}. CEO/CFO/COO buys = C-suite conviction (strongest signal). Directors = board approval (less valuable if alone). Cluster buying (3+) is statistically one of the most reliable predictors of future price appreciation.`}>
          <span className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-full text-sm font-medium border border-blue-500/30">
            👥 {insidersCount} Insiders ({roleBreakdownText})
          </span>
        </Tooltip>

        {/* Conviction Badge */}
        {skinInGame === 'YES' ? (
          <Tooltip text="HIGH CONVICTION = Insiders increased their ownership by 10%+ (major stake increase) OR bought $500k+. This means they're betting their own money heavily = strongest possible buy signal. They have insider information we don't.">
            <span className="px-3 py-1 bg-emerald-500/20 text-emerald-400 rounded-full text-sm font-medium border border-emerald-500/30">
              💎 HIGH CONVICTION
            </span>
          </Tooltip>
        ) : (
          <Tooltip text="Low conviction = small ownership increase or modest dollar amount. Could be routine buying or portfolio rebalancing rather than strong belief in upside.">
            <span className="px-3 py-1 bg-slate-700/50 text-slate-400 rounded-full text-sm font-medium border border-slate-600">
              Low Conviction
            </span>
          </Tooltip>
        )}
        
        {/* Event Classification Badge */}
        {eventBadge && (
          <Tooltip text={eventBadge.tooltip}>
            <span className={`px-3 py-1 rounded-full text-sm font-medium border ${eventBadge.colorClass}`}>
              {eventBadge.icon} {eventBadge.label}
            </span>
          </Tooltip>
        )}
      </div>

      {/* Trade Info */}
      <div className="space-y-3 mb-4">
        <div className="flex justify-between items-center">
          <Tooltip text={isSale
            ? "Total dollar amount insiders received from selling shares. Higher = bigger selloff. -$50k = casual, -$150k+ = noteworthy, -$500k+ = significant, -$1M+ = major liquidation."
            : "Total dollar amount insiders spent buying shares. Higher = more serious. $50k = casual, $150k+ = confident, $500k+ = very bullish, $1M+ = exceptional conviction."}>
            <span className="text-slate-400 text-sm border-b border-dotted border-slate-600 cursor-help">Trade Value</span>
          </Tooltip>
          <span className={`font-semibold ${isSale ? 'text-red-400' : 'text-white'}`}>{value}</span>
        </div>
        
        <div className="flex justify-between items-center">
          <Tooltip text={isSale 
            ? "How much their personal stake decreased. -5% = meaningful, -10% = significant, -20%+ = major selloff. For sales, this shows how much of their holdings they're dumping."
            : "How much their personal stake increased. +5% = meaningful, +10% = significant, +20%+ = major commitment. This shows conviction better than dollar amount - a CEO doubling their holdings is huge regardless of price."}>
            <span className="text-slate-400 text-sm border-b border-dotted border-slate-600 cursor-help">Ownership Change</span>
          </Tooltip>
          <span className={`font-semibold ${isSale ? 'text-red-400' : 'text-emerald-400'}`}>{deltaOwn}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-slate-400 text-sm">Trade Date</span>
          <span className="text-white text-sm">{tradeDate}</span>
        </div>

        {/* Upside */}
        {upside !== 'N/A' && (
          <div className="flex justify-between items-center pt-2 border-t border-slate-700">
            <Tooltip text="Gap between current price and Wall Street analyst average target. Positive = analysts think it's undervalued. +20%+ = significant upside potential. Combined with insider buying = high probability setup.">
              <span className="text-slate-400 text-sm border-b border-dotted border-slate-600 cursor-help">Upside to Target</span>
            </Tooltip>
            <span className={`font-bold text-lg ${upside.startsWith('+') ? 'text-emerald-400' : 'text-red-400'}`}>
              {upside}
            </span>
          </div>
        )}
      </div>

      {/* Health Flags */}
      {healthFlags && healthFlags !== 'N/A' && (
        <div className="bg-slate-900/50 rounded-lg p-3 mb-3">
          <Tooltip text="Financial health indicators from company fundamentals. Low Debt = safe balance sheet, Good Liquidity = can pay bills, Profitable = making money. High Conviction (Skin in Game) = exceptional setup. Avoid high debt + unprofitable unless you're very risk-tolerant.">
            <div className="text-xs text-slate-400 mb-1 border-b border-dotted border-slate-600 inline-block cursor-help">Financial Health</div>
          </Tooltip>
          <div className="text-sm text-slate-200">{healthFlags}</div>
        </div>
      )}

      {/* Sector Type Badge */}
      {sectorType && (
        <div className="mt-3">
          {sectorType.includes('DEFENSIVE') && (
            <Tooltip text="DEFENSIVE sectors (Healthcare, Consumer Staples, Utilities) = Safe havens during market downturns. These provide stability when AI bubble corrects. People always need medicine, food, electricity regardless of economy.">
              <div className="bg-green-500/10 border border-green-500/30 rounded-lg px-3 py-2">
                <div className="text-green-400 text-xs font-semibold">🛡️ {sectorType}</div>
              </div>
            </Tooltip>
          )}
          {sectorType.includes('AGGRESSIVE') && (
            <Tooltip text="AGGRESSIVE sectors = High risk/high reward. Sensitive to economic cycles, AI bubble risks, or market volatility. Can deliver huge gains but vulnerable in downturns. Only for risk-tolerant portfolios.">
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
                <div className="text-red-400 text-xs font-semibold">⚠️ {sectorType}</div>
              </div>
            </Tooltip>
          )}
          {sectorType.includes('NEUTRAL') && (
            <Tooltip text="NEUTRAL sectors = Balanced risk/reward. Not extremely defensive or aggressive. Moderate volatility and steady growth potential. Good for diversified portfolios.">
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg px-3 py-2">
                <div className="text-blue-400 text-xs font-semibold">⚖️ {sectorType}</div>
              </div>
            </Tooltip>
          )}
        </div>
      )}

      {/* Score Reasons */}
      {scoreReasons && scoreReasons !== 'N/A' && (
        <div className="mt-3 text-xs text-slate-400">
          <Tooltip text="Breakdown of why this stock got its Rainy Day Score. Shows which factors contributed: insider count, ownership change %, financial health, sector type. Helps you understand the conviction level.">
            <span className="font-semibold border-b border-dotted border-slate-600 cursor-help">Score Factors:</span>
          </Tooltip>
          {' '}{scoreReasons}
        </div>
      )}
    </div>
  );
};

export default TradeCard;
