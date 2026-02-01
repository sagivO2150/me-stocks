import { useState } from 'react';

function FilterPanel({ onRunScraper, isLoading }) {
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    minPrice: 5,
    filingDays: 30,
    minInsiders: 3,
    minValue: 150,
    includeCEO: true,
    includeCOO: true,
    includeCFO: true,
    includeDirector: true,
    numPages: 1
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onRunScraper(filters);
  };

  return (
    <div className="mb-8 bg-slate-800 rounded-lg p-6 border border-slate-700">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-white">🔧 Scraper Filters</h2>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition"
        >
          {showFilters ? 'Hide Filters' : 'Show Filters'}
        </button>
      </div>

      {showFilters && (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Price & Value Section */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-slate-300 mb-2">
                Minimum Stock Price ($)
              </label>
              <input
                type="number"
                value={filters.minPrice}
                onChange={(e) => setFilters({...filters, minPrice: parseFloat(e.target.value) || 0})}
                className="w-full px-4 py-2 bg-slate-700 text-white rounded-lg border border-slate-600 focus:border-emerald-500 focus:outline-none"
                step="0.01"
              />
            </div>

            <div>
              <label className="block text-slate-300 mb-2">
                Minimum Transaction Value ($k)
              </label>
              <input
                type="number"
                value={filters.minValue}
                onChange={(e) => setFilters({...filters, minValue: parseInt(e.target.value) || 0})}
                className="w-full px-4 py-2 bg-slate-700 text-white rounded-lg border border-slate-600 focus:border-emerald-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Time & Insiders Section */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label className="block text-slate-300 mb-2">
                Filing Within (days)
              </label>
              <input
                type="number"
                value={filters.filingDays}
                onChange={(e) => setFilters({...filters, filingDays: parseInt(e.target.value) || 0})}
                className="w-full px-4 py-2 bg-slate-700 text-white rounded-lg border border-slate-600 focus:border-emerald-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-slate-300 mb-2">
                Minimum Insiders
              </label>
              <input
                type="number"
                value={filters.minInsiders}
                onChange={(e) => setFilters({...filters, minInsiders: parseInt(e.target.value) || 0})}
                className="w-full px-4 py-2 bg-slate-700 text-white rounded-lg border border-slate-600 focus:border-emerald-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-slate-300 mb-2">
                Pages to Scrape
              </label>
              <input
                type="number"
                value={filters.numPages}
                onChange={(e) => setFilters({...filters, numPages: parseInt(e.target.value) || 1})}
                className="w-full px-4 py-2 bg-slate-700 text-white rounded-lg border border-slate-600 focus:border-emerald-500 focus:outline-none"
                min="1"
                max="5"
              />
            </div>
          </div>

          {/* Insider Roles Section */}
          <div>
            <label className="block text-slate-300 mb-3">
              Include Insider Roles
            </label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <label className="flex items-center space-x-2 text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.includeCEO}
                  onChange={(e) => setFilters({...filters, includeCEO: e.target.checked})}
                  className="w-5 h-5 text-emerald-500 bg-slate-700 border-slate-600 rounded focus:ring-emerald-500"
                />
                <span>CEO</span>
              </label>

              <label className="flex items-center space-x-2 text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.includeCOO}
                  onChange={(e) => setFilters({...filters, includeCOO: e.target.checked})}
                  className="w-5 h-5 text-emerald-500 bg-slate-700 border-slate-600 rounded focus:ring-emerald-500"
                />
                <span>COO</span>
              </label>

              <label className="flex items-center space-x-2 text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.includeCFO}
                  onChange={(e) => setFilters({...filters, includeCFO: e.target.checked})}
                  className="w-5 h-5 text-emerald-500 bg-slate-700 border-slate-600 rounded focus:ring-emerald-500"
                />
                <span>CFO</span>
              </label>

              <label className="flex items-center space-x-2 text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.includeDirector}
                  onChange={(e) => setFilters({...filters, includeDirector: e.target.checked})}
                  className="w-5 h-5 text-emerald-500 bg-slate-700 border-slate-600 rounded focus:ring-emerald-500"
                />
                <span>Director</span>
              </label>
            </div>
          </div>

          {/* Submit Button */}
          <div className="pt-4">
            <button
              type="submit"
              disabled={isLoading}
              className={`w-full py-3 rounded-lg font-bold text-white transition ${
                isLoading 
                  ? 'bg-slate-600 cursor-not-allowed' 
                  : 'bg-emerald-600 hover:bg-emerald-500'
              }`}
            >
              {isLoading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin h-5 w-5 mr-3" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Scraping Data...
                </span>
              ) : (
                '🚀 Run Scraper with These Filters'
              )}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default FilterPanel;
