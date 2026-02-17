import React, { useState, useEffect } from 'react';
import AllChartsView from './AllChartsView';

export default function GrovPocView() {
  const [pocData, setPocData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadPocData();
  }, []);

  const loadPocData = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:3001/api/grov-poc');
      const result = await response.json();
      
      if (result.success) {
        setPocData(result.data);
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-slate-400">Loading GROV POC data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-700 rounded-lg p-6 text-center">
        <p className="text-red-400 text-lg mb-2">❌ Error loading POC data</p>
        <p className="text-slate-400">{error}</p>
        <button
          onClick={loadPocData}
          className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!pocData) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 text-center">
        <p className="text-slate-400">No POC data available</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Card */}
      <div className="bg-gradient-to-r from-amber-900/30 to-orange-900/30 border border-amber-700/50 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-white">
            🧪 GROV Rise Explosion Strategy
          </h2>
          <div className="text-right">
            <div className="text-3xl font-bold text-green-400">
              +{pocData.roi.toFixed(2)}%
            </div>
            <div className="text-sm text-slate-400">ROI</div>
          </div>
        </div>
        
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-slate-900/50 rounded-lg p-4">
            <div className="text-2xl font-bold text-white">{pocData.total_trades}</div>
            <div className="text-sm text-slate-400">Total Trades</div>
          </div>
          <div className="bg-slate-900/50 rounded-lg p-4">
            <div className="text-2xl font-bold text-green-400">
              ${pocData.total_profit.toLocaleString()}
            </div>
            <div className="text-sm text-slate-400">Total Profit</div>
          </div>
          <div className="bg-slate-900/50 rounded-lg p-4">
            <div className="text-2xl font-bold text-blue-400">
              ${pocData.total_invested.toLocaleString()}
            </div>
            <div className="text-sm text-slate-400">Total Invested</div>
          </div>
        </div>
      </div>

      {/* Trades List */}
      <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-6">
        <h3 className="text-xl font-bold text-white mb-4">📊 Trade Details</h3>
        <div className="space-y-3">
          {pocData.trades.map((trade, idx) => (
            <div
              key={idx}
              className={`p-4 rounded-lg border ${
                trade.return_pct > 0
                  ? 'bg-green-900/20 border-green-700/50'
                  : 'bg-red-900/20 border-red-700/50'
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">#{idx + 1}</span>
                    <span className="font-mono text-white">
                      {trade.entry_date} → {trade.exit_date}
                    </span>
                    {trade.is_explosion === 'yes' && (
                      <span className="px-2 py-1 bg-amber-600 text-white text-xs font-bold rounded">
                        💥 EXPLOSION
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-slate-400 mt-1">
                    Insider: {trade.insider_name} (${(trade.insider_value / 1000).toFixed(0)}K) • 
                    Rise: +{trade.rise_pct}%
                  </div>
                </div>
                <div className="text-right">
                  <div className={`text-2xl font-bold ${
                    trade.return_pct > 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {trade.return_pct > 0 ? '+' : ''}{trade.return_pct.toFixed(1)}%
                  </div>
                  <div className="text-sm text-slate-400">
                    ${trade.entry_price.toFixed(2)} → ${trade.exit_price.toFixed(2)}
                  </div>
                  <div className={`text-lg font-bold ${
                    trade.profit_loss > 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {trade.profit_loss > 0 ? '+' : ''}${trade.profit_loss.toFixed(0)}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-6">
        <h3 className="text-xl font-bold text-white mb-4">📈 Price Chart with Signals</h3>
        <AllChartsView 
          stocks={[{ ticker: 'GROV' }]} 
          backtestTrades={pocData.trades.map(trade => ({
            ticker: 'GROV',
            entry_date: trade.entry_date,
            entry_price: trade.entry_price.toString(),
            exit_date: trade.exit_date,
            exit_price: trade.exit_price.toString(),
            return_pct: trade.return_pct.toString(),
            profit_loss: trade.profit_loss,
            position_size: trade.position_size,
            insider_purchase_date: trade.insider_date,
            is_explosion: trade.is_explosion
          }))}
        />
      </div>
    </div>
  );
}
