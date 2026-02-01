import { useState, useEffect } from 'react';
import Papa from 'papaparse';
import TradeCard from './components/TradeCard';
import FilterPanel from './components/FilterPanel';

function App() {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [scraperLoading, setScraperLoading] = useState(false);
  const [scraperMessage, setScraperMessage] = useState('');

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
            🏰 Insider Trading Fortress
          </h1>
          <p className="text-slate-300 text-lg">
            Smart Money Moves • Rainy Day Strategy
          </p>
          <div className="mt-4 inline-block bg-slate-800 rounded-lg px-6 py-3 border border-slate-700">
            <span className="text-slate-400">Found </span>
            <span className="text-emerald-400 font-bold text-xl">{trades.length}</span>
            <span className="text-slate-400"> high-conviction insider trades</span>
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
          {trades.map((trade, index) => (
            <TradeCard key={index} trade={trade} />
          ))}
        </div>

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
