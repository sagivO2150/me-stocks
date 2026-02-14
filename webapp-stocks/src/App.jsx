import { useState, useEffect } from 'react';
import Papa from 'papaparse';
import TradeCard from './components/TradeCard';
import PoliticalTradeCard from './components/PoliticalTradeCard';
import TopMonthlyCard from './components/TopMonthlyCard';
import LivePurchasesCard from './components/LivePurchasesCard';
import FilterPanel from './components/FilterPanel';
import StockDetail from './components/StockDetail';
import AllChartsView from './components/AllChartsView';

function App() {
  const [trades, setTrades] = useState([]);
  const [politicalTrades, setPoliticalTrades] = useState([]);
  const [topMonthlyTrades, setTopMonthlyTrades] = useState([]);
  const [livePurchases, setLivePurchases] = useState([]);
  const [politicalPagination, setPoliticalPagination] = useState({
    page: 1,
    limit: 50,
    total: 0,
    hasMore: false
  });
  const [politicalFilters, setPoliticalFilters] = useState({
    minAmount: 0,        // No minimum filter
    tradeType: 'all',
    party: 'all',
    chamber: 'all',
    days: 0              // No time limit - show all trades
  });
  const [viewMode, setViewMode] = useState('insider'); // 'insider', 'political', 'monthly', 'live', 'all-charts'
  const [monthlySortType, setMonthlySortType] = useState('amount'); // 'amount', 'c-level', '10-percent'
  const [loading, setLoading] = useState(true);
  const [politicalLoading, setPoliticalLoading] = useState(false);
  const [monthlyLoading, setMonthlyLoading] = useState(false);
  const [liveLoading, setLiveLoading] = useState(false);
  const [error, setError] = useState(null);
  const [scraperLoading, setScraperLoading] = useState(false);
  const [scraperMessage, setScraperMessage] = useState('');
  const [selectedTrade, setSelectedTrade] = useState(null);
  const [searchTicker, setSearchTicker] = useState('');

  const loadCSV = async () => {
    try {
      const response = await fetch('/openinsider_data_latest.csv?t=' + new Date().getTime());
      if (!response.ok) {
        throw new Error('Failed to load CSV file');
      }
      
      const csvText = await response.text();
      
      Papa.parse(csvText, {
        header: true,
        complete: (results) => {
          setTrades(results.data.filter(row => row.Ticker)); // Filter out empty rows
          setLoading(false);
        },
        error: (error) => {
          setError(error.message);
          setLoading(false);
        }
      });
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const loadPoliticalTrades = async (page = 1, filters = politicalFilters, append = false) => {
    setPoliticalLoading(true);
    
    try {
      // Build query params
      const params = new URLSearchParams({
        page: page.toString(),
        limit: '50'
      });
      
      console.log('Loading political trades with filters:', filters);
      
      if (filters.minAmount && filters.minAmount > 0) params.append('min_amount', filters.minAmount);
      if (filters.tradeType && filters.tradeType !== 'all') params.append('trade_type', filters.tradeType);
      if (filters.party && filters.party !== 'all') params.append('party', filters.party);
      if (filters.chamber && filters.chamber !== 'all') params.append('chamber', filters.chamber);
      if (filters.days && filters.days > 0) params.append('days', filters.days);
      
      const response = await fetch(`http://localhost:3001/api/political-trades?${params}`);
      if (!response.ok) {
        console.log('Political trades data not available yet');
        setPoliticalLoading(false);
        return;
      }
      
      const data = await response.json();
      if (data.success && data.trades) {
        if (append) {
          // Append for infinite scroll
          setPoliticalTrades(prev => [...prev, ...data.trades]);
        } else {
          // Replace for new filters
          setPoliticalTrades(data.trades);
        }
        setPoliticalPagination(data.pagination);
      }
    } catch (err) {
      console.error('Error loading political trades:', err.message);
    } finally {
      setPoliticalLoading(false);
    }
  };

  const loadTopMonthlyTrades = async () => {
    setMonthlyLoading(true);
    
    try {
      const response = await fetch('http://localhost:3001/api/top-monthly-trades');
      const data = await response.json();
      
      if (data.success && data.data) {
        setTopMonthlyTrades(data.data);
      }
    } catch (err) {
      console.error('Error loading top monthly trades:', err.message);
    } finally {
      setMonthlyLoading(false);
    }
  };

  const loadLivePurchases = async () => {
    setLiveLoading(true);
    
    try {
      const response = await fetch('http://localhost:3001/api/live-purchases');
      const data = await response.json();
      
      if (data.success && data.companies) {
        setLivePurchases(data.companies);
      } else {
        setLivePurchases([]);
      }
    } catch (err) {
      console.error('Error loading live purchases:', err.message);
      setLivePurchases([]);
    } finally {
      setLiveLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    const ticker = searchTicker.trim().toUpperCase();
    if (ticker) {
      setSelectedTrade({ Ticker: ticker, ticker: ticker });
      setSearchTicker('');
    }
  };

  const handleRunMonthlyUpdate = async () => {
    setScraperLoading(true);
    setScraperMessage('');
    
    try {
      const response = await fetch('http://localhost:3001/api/scrape-top-monthly', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      const data = await response.json();
      
      if (data.success) {
        setScraperMessage('✅ ' + data.message);
        // Reload monthly data after successful scrape
        setTimeout(() => {
          loadTopMonthlyTrades();
        }, 1000);
      } else {
        setScraperMessage('❌ ' + data.message);
      }
    } catch (err) {
      setScraperMessage('❌ Failed to update monthly data: ' + err.message);
    } finally {
      setScraperLoading(false);
      setTimeout(() => setScraperMessage(''), 5000);
    }
  };

  const handleRunLivePurchasesUpdate = async () => {
    setScraperLoading(true);
    setScraperMessage('Fetching live EDGAR purchases... This may take 30-60 seconds...');
    
    try {
      const response = await fetch('http://localhost:3001/api/scrape-live-purchases', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ days: 1 }) // Last 2 days (today + yesterday)
      });
      
      const data = await response.json();
      
      if (data.success) {
        setScraperMessage(`✅ Found ${data.total_companies} stocks with purchases today!`);
        setLivePurchases(data.companies || []);
      } else {
        setScraperMessage('❌ ' + (data.message || 'Failed to fetch live purchases'));
        setLivePurchases([]);
      }
    } catch (err) {
      setScraperMessage('❌ Failed to fetch live purchases: ' + err.message);
      setLivePurchases([]);
    } finally {
      setScraperLoading(false);
      setTimeout(() => setScraperMessage(''), 8000);
    }
  };

  const handleRunScraper = async (filters) => {
    setScraperLoading(true);
    setScraperMessage('');
    setError(null);

    try {
      const response = await fetch('http://localhost:3001/api/scrape', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(filters)
      });

      const data = await response.json();

      if (data.success) {
        setScraperMessage('✅ ' + data.message);
        // Reload CSV after successful scrape
        setTimeout(() => {
          loadCSV();
        }, 1000);
      } else {
        setScraperMessage('❌ ' + data.message);
        setError(data.error);
      }
    } catch (err) {
      setScraperMessage('❌ Failed to connect to backend server');
      setError(err.message);
    } finally {
      setScraperLoading(false);
      // Clear message after 5 seconds
      setTimeout(() => setScraperMessage(''), 5000);
    }
  };

  useEffect(() => {
    loadCSV();
    loadPoliticalTrades();
    loadTopMonthlyTrades();
    loadLivePurchases();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-linear-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-white text-2xl">Loading insider trades...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-linear-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-red-400 text-xl">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-linear-to-br from-slate-900 via-slate-800 to-slate-900 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-5xl font-bold text-white mb-3">
            🏰 Multi-Vector Intelligence Platform
          </h1>
          <p className="text-slate-300 text-lg mb-4">
            Smart Money Moves • Corporate Insiders • Political Intelligence
          </p>
          
          {/* Stock Search */}
          <form onSubmit={handleSearch} className="mb-6 max-w-md mx-auto">
            <div className="relative">
              <input
                type="text"
                value={searchTicker}
                onChange={(e) => setSearchTicker(e.target.value.toUpperCase())}
                placeholder="Search stock ticker (e.g., AAPL, TSLA, NVDA)..."
                className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
              />
              <button
                type="submit"
                className="absolute right-2 top-1/2 -translate-y-1/2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md transition font-medium"
              >
                🔍 Search
              </button>
            </div>
          </form>
          
          {/* View Mode Switcher */}
          <div className="mt-4 inline-flex bg-slate-800 rounded-lg p-1 border border-slate-700">
            <button
              onClick={() => setViewMode('insider')}
              className={`px-6 py-2 rounded-md font-medium transition ${
                viewMode === 'insider'
                  ? 'bg-emerald-600 text-white'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              📊 Corporate Insiders
            </button>
            <button
              onClick={() => setViewMode('political')}
              className={`px-6 py-2 rounded-md font-medium transition ${
                viewMode === 'political'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              🏛️ Political Trades
            </button>
            <button
              onClick={() => setViewMode('monthly')}
              className={`px-6 py-2 rounded-md font-medium transition ${
                viewMode === 'monthly'
                  ? 'bg-purple-600 text-white'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              🔥 Top Monthly Activity
            </button>
            <button
              onClick={() => setViewMode('live')}
              className={`px-6 py-2 rounded-md font-medium transition ${
                viewMode === 'live'
                  ? 'bg-red-600 text-white'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              🔴 Live Purchases
            </button>
            <button
              onClick={() => setViewMode('all-charts')}
              className={`px-6 py-2 rounded-md font-medium transition ${
                viewMode === 'all-charts'
                  ? 'bg-orange-600 text-white'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              📈 All Charts
            </button>
            <button
              onClick={() => setViewMode('all-charts-poc')}
              className={`px-6 py-2 rounded-md font-medium transition ${
                viewMode === 'all-charts-poc'
                  ? 'bg-amber-600 text-white'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              🧪 POC Charts
            </button>
          </div>

          <div className="mt-4 inline-block bg-slate-800 rounded-lg px-6 py-3 border border-slate-700">
            {viewMode === 'insider' && (
              <>
                <span className="text-slate-400">Found </span>
                <span className="text-emerald-400 font-bold text-xl">{trades.length}</span>
                <span className="text-slate-400"> high-conviction insider trades</span>
              </>
            )}
            {viewMode === 'political' && (
              <>
                <span className="text-slate-400">Found </span>
                <span className="text-blue-400 font-bold text-xl">{politicalTrades.length}</span>
                <span className="text-slate-400"> political trades</span>
              </>
            )}
            {viewMode === 'monthly' && (
              <>
                <span className="text-slate-400">Showing top </span>
                <span className="text-purple-400 font-bold text-xl">{topMonthlyTrades.length}</span>
                <span className="text-slate-400"> stocks by insider activity</span>
              </>
            )}
            {viewMode === 'live' && (
              <>
                <span className="text-slate-400">Found </span>
                <span className="text-red-400 font-bold text-xl">{livePurchases.length}</span>
                <span className="text-slate-400"> stocks with purchases today</span>
              </>
            )}
            {viewMode === 'all-charts' && (
              <>
                <span className="text-slate-400">Showing </span>
                <span className="text-orange-400 font-bold text-xl">{topMonthlyTrades.length}</span>
                <span className="text-slate-400"> charts with insider overlays</span>
              </>
            )}
            {viewMode === 'all-charts-poc' && (
              <>
                <span className="text-slate-400">Showing </span>
                <span className="text-amber-400 font-bold text-xl">2</span>
                <span className="text-slate-400"> POC charts (GME, HYMC)</span>
              </>
            )}
          </div>
        </div>

        {/* Filter Panel */}
        <FilterPanel 
          onRunScraper={handleRunScraper} 
          isLoading={scraperLoading} 
          viewMode={viewMode}
          onApplyPoliticalFilters={(filters) => {
            console.log('📊 App.jsx received filters:', filters);
            setPoliticalFilters(filters);
            loadPoliticalTrades(1, filters, false); // Reset to page 1 with new filters
          }}
          onUpdatePoliticalData={() => {
            // Reload political trades after update
            loadPoliticalTrades(1, politicalFilters, false);
          }}
          onUpdateMonthlyData={handleRunMonthlyUpdate}
          onUpdateLivePurchases={handleRunLivePurchasesUpdate}
        />

        {/* Scraper Message */}
        {scraperMessage && (
          <div className={`mb-6 p-4 rounded-lg ${
            scraperMessage.startsWith('✅') 
              ? 'bg-emerald-900/50 border border-emerald-700 text-emerald-300' 
              : 'bg-red-900/50 border border-red-700 text-red-300'
          }`}>
            {scraperMessage}
          </div>
        )}

        {/* Monthly Sort Dropdown */}
        {viewMode === 'monthly' && topMonthlyTrades.length > 0 && (
          <div className="mb-6 flex items-center gap-4">
            <span className="text-slate-400 text-sm font-medium">Sort by:</span>
            <select
              value={monthlySortType}
              onChange={(e) => setMonthlySortType(e.target.value)}
              className="px-4 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-purple-500 transition"
            >
              <option value="amount">💰 Biggest Trading Amount</option>
              <option value="c-level">🎯 Most C-Level Purchases</option>
              <option value="10-percent">🏢 Most 10%er Purchases</option>
              <option value="combined">🔥 Most Combined (C-Level + 10%ers)</option>
            </select>
          </div>
        )}

        {/* Trade Cards Grid */}
        {viewMode !== 'all-charts' && viewMode !== 'all-charts-poc' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Show insider trades */}
            {viewMode === 'insider' && trades.map((trade, index) => (
              <div key={`insider-${index}`} onClick={() => setSelectedTrade(trade)} className="cursor-pointer">
                <TradeCard trade={trade} />
              </div>
            ))}
            
            {/* Show political trades */}
            {viewMode === 'political' && politicalTrades.map((trade, index) => (
              <div key={`political-${trade.id || index}`} onClick={() => setSelectedTrade(trade)} className="cursor-pointer">
                <PoliticalTradeCard trade={trade} />
              </div>
            ))}
            
            {/* Show top monthly trades */}
            {viewMode === 'monthly' && (() => {
            // Sort monthly trades based on selected sort type
            const sortedTrades = [...topMonthlyTrades].sort((a, b) => {
              if (monthlySortType === 'amount') {
                return b.total_value - a.total_value;
              } else if (monthlySortType === 'c-level') {
                // Calculate C-level + Directors count
                const aCount = (a.role_counts.COB || 0) + (a.role_counts.CEO || 0) + 
                               (a.role_counts.Pres || 0) + (a.role_counts.CFO || 0) + 
                               (a.role_counts.COO || 0) + (a.role_counts.GC || 0) + 
                               (a.role_counts.Director || 0);
                const bCount = (b.role_counts.COB || 0) + (b.role_counts.CEO || 0) + 
                               (b.role_counts.Pres || 0) + (b.role_counts.CFO || 0) + 
                               (b.role_counts.COO || 0) + (b.role_counts.GC || 0) + 
                               (b.role_counts.Director || 0);
                return bCount - aCount;
              } else if (monthlySortType === '10-percent') {
                // Calculate 10% Owners count
                const aCount = (a.role_counts['10% Owner'] || 0);
                const bCount = (b.role_counts['10% Owner'] || 0);
                return bCount - aCount;
              } else if (monthlySortType === 'combined') {
                // Calculate combined C-level + Directors + 10% Owners count
                const aCount = (a.role_counts.COB || 0) + (a.role_counts.CEO || 0) + 
                               (a.role_counts.Pres || 0) + (a.role_counts.CFO || 0) + 
                               (a.role_counts.COO || 0) + (a.role_counts.GC || 0) + 
                               (a.role_counts.Director || 0) + (a.role_counts['10% Owner'] || 0);
                const bCount = (b.role_counts.COB || 0) + (b.role_counts.CEO || 0) + 
                               (b.role_counts.Pres || 0) + (b.role_counts.CFO || 0) + 
                               (b.role_counts.COO || 0) + (b.role_counts.GC || 0) + 
                               (b.role_counts.Director || 0) + (b.role_counts['10% Owner'] || 0);
                return bCount - aCount;
              }
              return 0;
            });
            
            return sortedTrades.map((stock, index) => (
              <div key={`monthly-${stock.ticker}-${index}`} onClick={() => setSelectedTrade({ Ticker: stock.ticker, ticker: stock.ticker, eventClassification: stock.eventClassification })} className="cursor-pointer">
                <TopMonthlyCard stock={stock} />
              </div>
            ));
          })()}
          
          {/* Show live purchases */}
          {viewMode === 'live' && (
            <>
              {liveLoading ? (
                <div className="col-span-full text-center text-slate-400 py-12">
                  Loading live purchases...
                </div>
              ) : livePurchases.length === 0 ? (
                <div className="col-span-full bg-slate-800/50 border border-slate-700 rounded-lg p-8 text-center">
                  <div className="text-slate-300 text-xl mb-4">🔴 No Live Purchase Data</div>
                  <div className="text-slate-400 text-sm mb-4">
                    Click "Update Live Purchases" to fetch today's insider buying activity from SEC EDGAR.
                  </div>
                  <div className="text-slate-500 text-xs">
                    This will scan Form 4 filings from today and analyze:
                    <ul className="mt-2 space-y-1">
                      <li>• Shopping sprees (multiple insiders buying)</li>
                      <li>• C-suite purchases (CEO, CFO, COO)</li>
                      <li>• Large purchase signals vs. historical data</li>
                    </ul>
                  </div>
                </div>
              ) : (
                livePurchases.map((stock, index) => (
                  <div key={`live-${stock.ticker}-${index}`}>
                    <LivePurchasesCard 
                      stock={stock} 
                      onClick={() => setSelectedTrade({ Ticker: stock.ticker, ticker: stock.ticker, eventClassification: stock.eventClassification })}
                    />
                  </div>
                ))
              )}
            </>
          )}
          
          {/* No results message for political trades */}
          {viewMode === 'political' && !politicalLoading && politicalTrades.length === 0 && (
            <div className="col-span-full bg-yellow-900/30 border border-yellow-700 rounded-lg p-8 text-center">
              <div className="text-yellow-300 text-xl mb-2">⚠️ No trades found</div>
              <div className="text-yellow-200 text-sm">
                <p className="mb-2">No political trades match your current filters.</p>
                <p>Try adjusting your filters:</p>
                <ul className="mt-2 text-left inline-block">
                  <li>• Increase "Days Back" to 365 or more</li>
                  <li>• Lower minimum amount to $1K</li>
                  <li>• Select "All Parties" and "Both Chambers"</li>
                </ul>
              </div>
            </div>
          )}
          
          {/* No results message for monthly trades */}
          {viewMode === 'monthly' && !monthlyLoading && topMonthlyTrades.length === 0 && (
            <div className="col-span-full bg-yellow-900/30 border border-yellow-700 rounded-lg p-8 text-center">
              <div className="text-yellow-300 text-xl mb-2">⚠️ No monthly data available</div>
              <div className="text-yellow-200 text-sm">
                <p className="mb-2">Monthly insider trading data hasn't been loaded yet.</p>
                <p>Click the "Update Monthly Data" button in the filter panel to fetch the latest data.</p>
              </div>
            </div>
          )}
          </div>
        )}

        {/* All Charts View */}
        {viewMode === 'all-charts' && (
          <>
            {monthlyLoading ? (
              <div className="text-center text-slate-400 py-12">
                Loading charts...
              </div>
            ) : topMonthlyTrades.length === 0 ? (
              <div className="bg-yellow-900/30 border border-yellow-700 rounded-lg p-8 text-center">
                <div className="text-yellow-300 text-xl mb-2">⚠️ No monthly data available</div>
                <div className="text-yellow-200 text-sm">
                  <p className="mb-2">Monthly insider trading data hasn't been loaded yet.</p>
                  <p>Click the "Update Monthly Data" button in the filter panel to fetch the latest data.</p>
                </div>
              </div>
            ) : (
              <AllChartsView stocks={topMonthlyTrades} />
            )}
          </>
        )}

        {/* POC Charts View (GME + HYMC) */}
        {viewMode === 'all-charts-poc' && (
          <AllChartsView stocks={[{ ticker: 'GME' }, { ticker: 'HYMC' }]} />
        )}

        {/* Load More Button for Political Trades */}
        {viewMode === 'political' && politicalPagination.hasMore && (
          <div className="mt-8 text-center">
            <button
              onClick={() => loadPoliticalTrades(politicalPagination.page + 1, politicalFilters, true)}
              disabled={politicalLoading}
              className="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {politicalLoading ? '⏳ Loading...' : `📄 Load More (${politicalTrades.length} of ${politicalPagination.total})`}
            </button>
          </div>
        )}

        {/* Stock Detail Modal */}
        {selectedTrade && (
          <StockDetail trade={selectedTrade} onClose={() => setSelectedTrade(null)} />
        )}

        {/* Footer */}
        <div className="mt-12 text-center text-slate-500 text-sm">
          <p>Data sourced from OpenInsider + Yahoo Finance</p>
          <p className="mt-2">🔒 Not financial advice. For research purposes only.</p>
        </div>
      </div>
    </div>
  );
}

export default App;