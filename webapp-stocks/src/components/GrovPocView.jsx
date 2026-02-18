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
            🧪 {pocData.strategy || 'GROV Strategy'}
          </h2>
          <div className="text-right">
            <div className="text-3xl font-bold text-green-400">
              +{pocData.roi.toFixed(2)}%
            </div>
            <div className="text-sm text-slate-400">ROI</div>
          </div>
        </div>
        
        <div className="grid grid-cols-4 gap-4">
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
          {pocData.win_rate !== undefined && (
            <div className="bg-slate-900/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-cyan-400">
                {pocData.win_rate.toFixed(1)}%
              </div>
              <div className="text-sm text-slate-400">Win Rate</div>
            </div>
          )}
        </div>
      </div>

      {/* Chart with Buy/Sell Markers */}
      <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-6">
        <h3 className="text-xl font-bold text-white mb-4">📈 Price Chart with Trades</h3>
        <AllChartsView 
          stocks={[{ ticker: 'GROV' }]} 
          backtestTrades={pocData.trades || []}
        />
      </div>
    </div>
  );
}
