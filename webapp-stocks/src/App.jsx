import { useState, useEffect } from 'react';
import Papa from 'papaparse';
import TradeCard from './components/TradeCard';
import PoliticalTradeCard from './components/PoliticalTradeCard';
import FilterPanel from './components/FilterPanel';
import StockDetail from './components/StockDetail';

function App() {
  const [trades, setTrades] = useState([]);
  const [politicalTrades, setPoliticalTrades] = useState([]);
  const [viewMode, setViewMode] = useState('insider'); // 'insider', 'political', or 'both'
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [scraperLoading, setScraperLoading] = useState(false);
  const [scraperMessage, setScraperMessage] = useState('');
  const [selectedTrade, setSelectedTrade] = useState(null);

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

  const loadPoliticalCSV = async () => {
    try {
      const response = await fetch('http://localhost:3001/api/political-trades');
      if (!response.ok) {
        console.log('Political trades data not available yet');
        return;
      }
      
      const csvText = await response.text();
      
      Papa.parse(csvText, {
        header: true,
        complete: (results) => {
          setPoliticalTrades(results.data.filter(row => row.ticker)); // Filter out empty rows
        },
        error: (error) => {
          console.error('Error parsing political trades:', error.message);
        }
      });
    } catch (err) {
      console.error('Error loading political trades:', err.message);
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
    loadPoliticalCSV();
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
              onClick={() => setViewMode('both')}
              className={`px-6 py-2 rounded-md font-medium transition ${
                viewMode === 'both'
                  ? 'bg-purple-600 text-white'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              🔥 Combined View
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
            {viewMode === 'both' && (
              <>
                <span className="text-emerald-400 font-bold text-xl">{trades.length}</span>
                <span className="text-slate-400"> insiders + </span>
                <span className="text-blue-400 font-bold text-xl">{politicalTrades.length}</span>
                <span className="text-slate-400"> political trades</span>
              </>
            )}
          </div>
        </div>

        {/* Filter Panel */}
        <FilterPanel onRunScraper={handleRunScraper} isLoading={scraperLoading} />

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

        {/* Trade Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Show insider trades */}
          {(viewMode === 'insider' || viewMode === 'both') && trades.map((trade, index) => (
            <div key={`insider-${index}`} onClick={() => setSelectedTrade(trade)} className="cursor-pointer">
              <TradeCard trade={trade} />
            </div>
          ))}
          
          {/* Show political trades */}
          {(viewMode === 'political' || viewMode === 'both') && politicalTrades.map((trade, index) => (
            <div key={`political-${index}`} onClick={() => setSelectedTrade(trade)} className="cursor-pointer">
              <PoliticalTradeCard trade={trade} />
            </div>
          ))}
        </div>

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
