# GitHub Copilot Instructions for Stocks Analysis Project

## General Rules

- Never create a new file unless the user explicitly confirms it
- Never run git commit, push, or any VCS action on behalf of the user
- Always wait until the user has reviewed terminal output before ending the session
- Never create README.md or .md documentation files unless explicitly requested
- Never create or delete folders - only the user can do this manually

## Python Development

### Environment & Execution
- Always use the virtual environment's Python binary (`.venv/bin/python`)
- Always provide the full absolute path to scripts
- Never simplify commands to `python file.py` or `cd … && python file.py`
- Use `.venv/bin/python /absolute/path/to/script.py` format

### Code Style
- Use type hints for function parameters and return values
- Use docstrings for all functions explaining purpose, parameters, and returns
- Prefer pandas for data manipulation over manual loops
- Use multiprocessing Pool for parallel data fetching
- Handle yfinance errors gracefully with try/except blocks

### Script Organization
Follow the organized folder structure in `scripts/`:
- `core/`: Production scripts used by webapp (fetch_insider_trades.py, etc.)
- `data_sources/`: Data fetching organized by source (edgar/, openinsider/, quiver/, political/)
- `backtests/`: Strategy backtest files
- `analysis/`: Analysis and research scripts
- `debug/`: Debugging specific trade issues
- `testing/`: POC and experimental tests
- `utils/`: Utility scripts

## Critical: Chunked File System

**NEVER edit these files directly - they will be overwritten:**
- `webapp/app.py` (Flask backend)
- `webapp-react/components/dashboard.tsx` (React UI)

These files are split into chunks due to size limitations:
- `webapp/app_chunks/app-part1.txt` through `app-part5.txt`
- `webapp-react/components/dashboard/dashboard-part1.txt` through `dashboard-part7.txt`

**Editing workflow:**
1. Find the correct chunk file using grep
2. Edit the chunk file (`.txt` file)
3. Choose restart method:
   - Dashboard only? Run `cd webapp-react/components/dashboard && ./reassemble.sh`
   - Flask backend? Run `./restart_webapp.sh`
4. Verify both chunk AND main file show in `git status`

## Testing & Debugging

### Test Execution
- Always run tests after making changes to verify correctness
- If a test fails, add debug logs or suggest fixes, then re-run only after user confirmation
- Use existing tests in `scripts/testing/` rather than creating new standalone tests
- Incorporate new web UI tests into `webapp-react/__tests__/interactive_tests.py`

### Debugging
- When debugging trades, create files in `scripts/debug/` folder
- Use descriptive filenames like `debug_<ticker>_<date>.py`
- Include date ranges and specific price points in debug output

## File Movement & Imports

- When moving files to different folders, always update all import statements in other files
- When moving log files, update the script that generates them to save to the new location
- Use absolute imports for cross-module references
- Test imports after reorganizing files

## Strategy Development

### Backtesting
- Save backtest results to `output CSVs/backtest_<strategy_name>_results.csv`
- Include these metrics: ROI, win rate, avg return, median return, exit reasons
- Show trade-by-trade details with entry/exit dates and prices
- Calculate peak gain to understand missed opportunities
- Use business days only (pandas `bdate_range`)

### Entry Criteria
- Filter stocks with entry price < $5 (penny stocks underperform)
- Wait for explosive catalyst (>20% gain in 3-5 days)
- Use percentage-based slopes, not dollar amounts (5%/day, 3%/day thresholds)
- Apply 2-day grace period before any exits

### Exit Criteria
- Stop loss: -5% from entry (active before catalyst or after expiration)
- Trend reversal: Second dip after failed recovery
- Use slope comparison: second dip ≥50% of first dip slope AND ≥3%/day
- Catalyst expiration: 15 days since peak OR 15% drawdown

## Web App Development

### React/TypeScript Frontend
- Use functional components with hooks
- Prefer TypeScript interfaces over types for object shapes
- Use Tailwind CSS for styling
- Keep components focused - split large files into smaller modules
- Use React Query for data fetching and caching

### Flask Backend
- Use blueprints for route organization
- Return JSON responses with consistent structure: `{success: bool, data: any, error: string?}`
- Handle errors with try/except and return appropriate HTTP status codes
- Use path.join for file paths to ensure cross-platform compatibility

### Server Restart
- Use `./restart_webapp_stocks.sh` to restart both Node backend and Vite dev server
- Never use CSS selectors to start the webapp - use the restart script
- Ports: Node backend on 3001, Vite dev server on 5173
- Check process status with: `ps aux | grep 'vite.*stocks/webapp-stocks\|node.*server.js'`

## Data Files

### Location Standards
- Input data: `output CSVs/merged_insider_trades.json`
- Backtest results: `output CSVs/backtest_<name>_results.csv`
- Logs: `logs/` folder with descriptive names
- Temporary files: Use system temp directory, clean up after use

### Data Integrity
- Always validate JSON structure before processing
- Handle missing fields gracefully with `.get()` methods
- Check for empty DataFrames before operations
- Use pandas `.isna()` to detect missing values

## Example Code Patterns

### Running Python Scripts
```bash
# Correct
.venv/bin/python /Users/sagiv.oron/Documents/scripts_playground/stocks/scripts/backtests/backtest_trend_following.py

# Wrong - never do this
python script.py
cd folder && python script.py
```

### Editing Chunked Files
```bash
# 1. Find the chunk
grep -n "function_name" webapp/app_chunks/app-part*.txt

# 2. Edit app-part3.txt (the chunk file)

# 3. Restart to reassemble
./restart_webapp.sh
```

### Backtest Results Format
```python
closed_trades.append({
    'ticker': ticker,
    'entry_date': entry_date,
    'entry_price': entry_price,
    'exit_date': exit_date,
    'exit_price': exit_price,
    'exit_reason': reason,  # 'stop_loss', 'trend_reversal', 'end_of_period'
    'return_pct': return_pct,
    'days_held': days_held,
    'peak_gain': peak_gain
})
```

## Performance Optimization

- Use multiprocessing for fetching multiple tickers
- Cache yfinance data to avoid repeated API calls
- Use pandas vectorized operations instead of iterrows()
- Filter data early to reduce processing time
- Show progress indicators for long-running operations

## Documentation Style

- Use clear, concise docstrings with purpose, params, and returns
- Comment complex logic with "why" not "what"
- Include examples for non-obvious functions
- Keep inline comments short and to the point
- Use type hints as living documentation
