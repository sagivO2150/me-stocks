# Stocks WebApp - OpenInsider Scraper with Adjustable Filters

## Overview
This web application allows you to scrape insider trading data from OpenInsider with **customizable filters** directly from the browser.

## Features
- ✅ Adjustable filters (price, filing days, insider roles, transaction value, etc.)
- ✅ Real-time scraping via web UI
- ✅ Financial health analysis (Rainy Day Score, Beta, Institutional Ownership)
- ✅ Single CSV file that updates automatically
- ✅ Beautiful React frontend with Tailwind CSS

## Architecture
1. **Python Script** (`scripts/openinsider_scraper.py`) - Scrapes OpenInsider with command-line arguments
2. **Express Backend** (`webapp-stocks/server.js`) - API server that runs the Python script
3. **React Frontend** (`webapp-stocks/src/`) - User interface with filter controls

## Quick Start

### Option 1: Run Both Servers Manually

**Terminal 1 - Backend Server:**
```bash
cd webapp-stocks
npm run server
```

**Terminal 2 - Frontend Server:**
```bash
cd webapp-stocks
npm run dev
```

Then open: http://localhost:5173

### Option 2: Use the Restart Script
```bash
./restart_webapp_stocks.sh
```

## How to Use

1. **Open the Web App** at http://localhost:5173
2. **Click "Show Filters"** to expand the filter panel
3. **Adjust the filters:**
   - Minimum Stock Price
   - Filing Within Days
   - Minimum Insiders
   - Minimum Transaction Value
   - Include/Exclude CEO, COO, CFO, Director
   - Number of Pages to Scrape
4. **Click "Run Scraper with These Filters"**
5. **Wait** for the scraper to finish (you'll see a success message)
6. **View the updated data** - the page automatically reloads with new results

## Filter Explanations

- **Minimum Stock Price ($)**: Only include stocks above this price
- **Filing Within (days)**: Only include trades filed within the last X days
- **Minimum Insiders**: Minimum number of insiders who bought
- **Minimum Transaction Value ($k)**: Minimum total transaction value in thousands
- **Insider Roles**: Which executive roles to include (CEO, COO, CFO, Director)
- **Pages to Scrape**: Number of result pages to fetch (1-5, more = more data but slower)

## File Structure

```
stocks/
├── scripts/
│   └── openinsider_scraper.py    # Python scraper with CLI args
├── webapp-stocks/
│   ├── server.js                  # Express backend API
│   ├── src/
│   │   ├── App.jsx                # Main React component
│   │   └── components/
│   │       ├── FilterPanel.jsx    # Filter controls UI
│   │       └── TradeCard.jsx      # Individual trade display
│   └── public/
│       └── openinsider_data_latest.csv  # Updated by scraper
├── output CSVs/
│   └── openinsider_data_latest.csv     # Source CSV file
└── restart_webapp_stocks.sh       # Startup script
```

## API Endpoints

### POST /api/scrape
Runs the Python scraper with custom filters.

**Request Body:**
```json
{
  "minPrice": 5,
  "filingDays": 30,
  "minInsiders": 3,
  "minValue": 150,
  "includeCEO": true,
  "includeCOO": true,
  "includeCFO": true,
  "includeDirector": true,
  "numPages": 1
}
```

**Response:**
```json
{
  "success": true,
  "message": "Data scraped and updated successfully!",
  "output": "..."
}
```

## Troubleshooting

### Backend server not starting
```bash
# Check if port 3001 is already in use
lsof -ti:3001 | xargs kill -9

# Then restart
cd webapp-stocks
npm run server
```

### Frontend not connecting to backend
- Make sure backend is running on port 3001
- Check browser console for CORS errors
- Verify the backend URL in App.jsx is `http://localhost:3001`

### Python script errors
```bash
# Test the script directly
/opt/homebrew/bin/python3 scripts/openinsider_scraper.py --help

# Run with default filters
/opt/homebrew/bin/python3 scripts/openinsider_scraper.py
```

## Development

To modify filters:
1. **Backend**: Update `server.js` to handle new parameters
2. **Frontend**: Add new form inputs in `FilterPanel.jsx`
3. **Python**: Add new CLI arguments in `openinsider_scraper.py`

## Notes

- The CSV file is always named `openinsider_data_latest.csv` (no more timestamps!)
- Each scrape overwrites the previous data
- The webapp automatically refreshes after a successful scrape
- Be respectful to OpenInsider - don't scrape too frequently or too many pages
