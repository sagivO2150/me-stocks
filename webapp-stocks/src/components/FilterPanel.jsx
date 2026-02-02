import { useState } from 'react';
import Tooltip from './Tooltip';

function FilterPanel({ onRunScraper, isLoading }) {
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    minPrice: 5,
    filingDays: 30,
    minInsiders: 3,
    minValue: 150,
    minOwnChange: 0,
    tradeType: 'purchase',
    includeCOB: true,
    includeCEO: true,
    includePres: true,
    includeCOO: true,
    includeCFO: true,
    includeGC: true,
    includeVP: true,
    includeDirector: true,
    include10Owner: true,
    includeOther: true
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onRunScraper(filters);
  };

  const toggleCLevelRoles = () => {
    const allCLevelEnabled = filters.includeCOB && filters.includeCEO && filters.includePres && 
                             filters.includeCOO && filters.includeCFO && filters.includeGC && filters.includeVP;
    setFilters({
      ...filters,
      includeCOB: !allCLevelEnabled,
      includeCEO: !allCLevelEnabled,
      includePres: !allCLevelEnabled,
      includeCOO: !allCLevelEnabled,
      includeCFO: !allCLevelEnabled,
      includeGC: !allCLevelEnabled,
      includeVP: !allCLevelEnabled
    });
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
          {/* Trade Type Toggle */}
          <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
            <label className="block text-slate-300 mb-3">
              <Tooltip text="Choose whether to search for insider purchases (bullish signal - insiders buying stock) or sales (could indicate various reasons - profit taking, portfolio rebalancing, or concern about company).">
                <span className="border-b border-dotted border-slate-500">Trade Type</span>
              </Tooltip>
            </label>
            <div className="flex items-center space-x-4">
              <label className="flex items-center space-x-3 cursor-pointer">
                <input
                  type="radio"
                  name="tradeType"
                  value="purchase"
                  checked={filters.tradeType === 'purchase'}
                  onChange={(e) => setFilters({...filters, tradeType: e.target.value})}
                  className="w-5 h-5 text-emerald-500 bg-slate-700 border-slate-600 focus:ring-emerald-500"
                />
                <span className="text-slate-200 font-medium">📈 Purchases (Bullish)</span>
              </label>
              <label className="flex items-center space-x-3 cursor-pointer">
                <input
                  type="radio"
                  name="tradeType"
                  value="sale"
                  checked={filters.tradeType === 'sale'}
                  onChange={(e) => setFilters({...filters, tradeType: e.target.value})}
                  className="w-5 h-5 text-red-500 bg-slate-700 border-slate-600 focus:ring-red-500"
                />
                <span className="text-slate-200 font-medium">📉 Sales (Bearish)</span>
              </label>
            </div>
          </div>

          {/* Price & Value Section */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-slate-300 mb-2">
                <Tooltip text="Filters out penny stocks. Higher = fewer results but more established companies. Lower = more opportunities but riskier. Sweet spot: $5-$20 for quality small/mid caps.">
                  <span className="border-b border-dotted border-slate-500">Minimum Stock Price ($)</span>
                </Tooltip>
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
                <Tooltip text={filters.tradeType === 'purchase' 
                  ? "Total dollar value of insider purchases. Higher = insiders putting more 'skin in the game' = stronger conviction signal. $50k = casual buy, $150k+ = serious confidence, $500k+ = very bullish."
                  : "Total dollar value of insider sales. Higher = more significant sale. Note: Sales can happen for many reasons (diversification, liquidity needs, not always bearish)."}>
                  <span className="border-b border-dotted border-slate-500">Minimum Transaction Value ($k)</span>
                </Tooltip>
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
                <Tooltip text="How recent the insider trades are. Lower = more current data but fewer results. 30 days = catch fresh momentum, 60-90 days = broader view. Insiders must file within 2 business days of trading.">
                  <span className="border-b border-dotted border-slate-500">Filing Within (days)</span>
                </Tooltip>
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
                <Tooltip text="Cluster buying = powerful signal. 1 insider = maybe personal reasons. 3+ insiders buying together = they know something. 5+ = extremely bullish consensus. This is one of the strongest predictors.">
                  <span className="border-b border-dotted border-slate-500">Minimum Insiders</span>
                </Tooltip>
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
                <Tooltip text={filters.tradeType === 'purchase' 
                  ? "Minimum ownership increase percentage. 0% = any increase, 10%+ = meaningful commitment, 50%+ = major stake increase, 100%+ = doubling or more. Higher values = stronger conviction but fewer results. Filters for 'skin in the game'."
                  : "Minimum ownership decrease percentage (how much they sold). 0% = any sale, 10%+ = meaningful reduction, 50%+ = major stake decrease. For sales, this represents the % of holdings they sold off."}>
                  <span className="border-b border-dotted border-slate-500">
                    Min Ownership Chg (%)
                    {filters.tradeType === 'sale' && ' - Decrease'}
                  </span>
                </Tooltip>
              </label>
              <input
                type="number"
                value={filters.minOwnChange}
                onChange={(e) => setFilters({...filters, minOwnChange: parseInt(e.target.value) || 0})}
                className="w-full px-4 py-2 bg-slate-700 text-white rounded-lg border border-slate-600 focus:border-emerald-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Insider Titles Section */}
          <div>
            <label className="block text-slate-300 mb-3">
              <Tooltip text="Filter by insider title. C-Level = top executives with strategic knowledge (strongest buy signals). Director = board members. 10% Owner = major shareholders. Other = various roles.">
                <span className="border-b border-dotted border-slate-500">Include Insider Titles</span>
              </Tooltip>
            </label>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* C-Level Section */}
              <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
                <div className="flex justify-between items-center mb-3">
                  <div className="text-sm font-semibold text-emerald-400">👔 C-Level Officers</div>
                  <button
                    type="button"
                    onClick={toggleCLevelRoles}
                    className="text-xs px-2 py-1 bg-slate-600 hover:bg-slate-500 text-slate-300 rounded transition"
                  >
                    Toggle All
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <label className="flex items-center space-x-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filters.includeCOB}
                      onChange={(e) => setFilters({...filters, includeCOB: e.target.checked})}
                      className="w-4 h-4 text-emerald-500 bg-slate-700 border-slate-600 rounded focus:ring-emerald-500"
                    />
                    <span className="text-sm">COB</span>
                  </label>

                  <label className="flex items-center space-x-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filters.includeCEO}
                      onChange={(e) => setFilters({...filters, includeCEO: e.target.checked})}
                      className="w-4 h-4 text-emerald-500 bg-slate-700 border-slate-600 rounded focus:ring-emerald-500"
                    />
                    <span className="text-sm">CEO</span>
                  </label>

                  <label className="flex items-center space-x-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filters.includePres}
                      onChange={(e) => setFilters({...filters, includePres: e.target.checked})}
                      className="w-4 h-4 text-emerald-500 bg-slate-700 border-slate-600 rounded focus:ring-emerald-500"
                    />
                    <span className="text-sm">Pres</span>
                  </label>

                  <label className="flex items-center space-x-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filters.includeCOO}
                      onChange={(e) => setFilters({...filters, includeCOO: e.target.checked})}
                      className="w-4 h-4 text-emerald-500 bg-slate-700 border-slate-600 rounded focus:ring-emerald-500"
                    />
                    <span className="text-sm">COO</span>
                  </label>

                  <label className="flex items-center space-x-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filters.includeCFO}
                      onChange={(e) => setFilters({...filters, includeCFO: e.target.checked})}
                      className="w-4 h-4 text-emerald-500 bg-slate-700 border-slate-600 rounded focus:ring-emerald-500"
                    />
                    <span className="text-sm">CFO</span>
                  </label>

                  <label className="flex items-center space-x-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filters.includeGC}
                      onChange={(e) => setFilters({...filters, includeGC: e.target.checked})}
                      className="w-4 h-4 text-emerald-500 bg-slate-700 border-slate-600 rounded focus:ring-emerald-500"
                    />
                    <span className="text-sm">GC</span>
                  </label>

                  <label className="flex items-center space-x-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filters.includeVP}
                      onChange={(e) => setFilters({...filters, includeVP: e.target.checked})}
                      className="w-4 h-4 text-emerald-500 bg-slate-700 border-slate-600 rounded focus:ring-emerald-500"
                    />
                    <span className="text-sm">VP</span>
                  </label>
                </div>
              </div>
              
              {/* Other Roles Section */}
              <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
                <div className="text-sm font-semibold text-blue-400 mb-3">📋 Other Roles</div>
                <div className="grid grid-cols-1 gap-2">
                  <label className="flex items-center space-x-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filters.includeDirector}
                      onChange={(e) => setFilters({...filters, includeDirector: e.target.checked})}
                      className="w-4 h-4 text-blue-500 bg-slate-700 border-slate-600 rounded focus:ring-blue-500"
                    />
                    <span className="text-sm">Director</span>
                  </label>

                  <label className="flex items-center space-x-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filters.include10Owner}
                      onChange={(e) => setFilters({...filters, include10Owner: e.target.checked})}
                      className="w-4 h-4 text-blue-500 bg-slate-700 border-slate-600 rounded focus:ring-blue-500"
                    />
                    <span className="text-sm">10% Owner</span>
                  </label>

                  <label className="flex items-center space-x-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filters.includeOther}
                      onChange={(e) => setFilters({...filters, includeOther: e.target.checked})}
                      className="w-4 h-4 text-blue-500 bg-slate-700 border-slate-600 rounded focus:ring-blue-500"
                    />
                    <span className="text-sm">Other</span>
                  </label>
                </div>
              </div>
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
