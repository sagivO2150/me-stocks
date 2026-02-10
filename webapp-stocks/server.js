import express from 'express';
import { spawn } from 'child_process';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';
import Database from 'better-sqlite3';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Initialize SQLite database for political trades
const dbPath = path.join(__dirname, 'political_trades.db');
const db = new Database(dbPath);
console.log(`📊 Connected to political trades database: ${dbPath}`);

const app = express();
app.use(cors());
app.use(express.json());

const PORT = 3001;

// Endpoint to run the Python scraper with custom filters
app.post('/api/scrape', (req, res) => {
  const {
    minPrice = 5,
    filingDays = 30,
    minInsiders = 3,
    minValue = 150,
    minOwnChange = 0,
    tradeType = 'purchase',
    includeCOB = true,
    includeCEO = true,
    includePres = true,
    includeCOO = true,
    includeCFO = true,
    includeGC = true,
    includeVP = true,
    includeDirector = true,
    include10Owner = true,
    includeOther = true
  } = req.body;

  console.log('Starting scraper with filters:', req.body);

  const pythonScript = path.join(__dirname, '../scripts/openinsider_scraper.py');
  const args = [
    pythonScript,
    '--min-price', minPrice.toString(),
    '--filing-days', filingDays.toString(),
    '--min-insiders', minInsiders.toString(),
    '--min-value', minValue.toString(),
    '--min-own-change', minOwnChange.toString(),
    '--trade-type', tradeType,
    '--include-cob', includeCOB ? '1' : '0',
    '--include-ceo', includeCEO ? '1' : '0',
    '--include-pres', includePres ? '1' : '0',
    '--include-coo', includeCOO ? '1' : '0',
    '--include-cfo', includeCFO ? '1' : '0',
    '--include-gc', includeGC ? '1' : '0',
    '--include-vp', includeVP ? '1' : '0',
    '--include-director', includeDirector ? '1' : '0',
    '--include-10owner', include10Owner ? '1' : '0',
    '--include-other', includeOther ? '1' : '0'
  ];

  const pythonProcess = spawn('/opt/homebrew/bin/python3', args);
  
  let output = '';
  let errorOutput = '';

  pythonProcess.stdout.on('data', (data) => {
    const chunk = data.toString();
    output += chunk;
    console.log(chunk);
  });

  pythonProcess.stderr.on('data', (data) => {
    const chunk = data.toString();
    errorOutput += chunk;
    console.error(chunk);
  });

  pythonProcess.on('close', (code) => {
    if (code === 0) {
      console.log('Scraper completed successfully');
      
      // Copy the CSV to the public folder for the webapp
      const sourceCSV = path.join(__dirname, '../output CSVs/openinsider_data_latest.csv');
      const destCSV = path.join(__dirname, 'public/openinsider_data_latest.csv');
      
      fs.copyFile(sourceCSV, destCSV, (err) => {
        if (err) {
          console.error('Error copying CSV:', err);
          res.status(500).json({ 
            success: false, 
            message: 'Scraper completed but failed to copy CSV',
            error: err.message 
          });
        } else {
          console.log('CSV copied to public folder');
          res.json({ 
            success: true, 
            message: 'Data scraped and updated successfully!',
            output: output
          });
        }
      });
    } else {
      console.error(`Scraper exited with code ${code}`);
      res.status(500).json({ 
        success: false, 
        message: `Scraper failed with exit code ${code}`,
        error: errorOutput 
      });
    }
  });
});

// Stock history endpoint
app.get('/api/stock-history/:ticker', (req, res) => {
  const ticker = req.params.ticker.toUpperCase();
  const period = req.query.period || '1y'; // Default to 1 year
  
  console.log(`Fetching stock history for ${ticker}, period: ${period}`);
  
  const pythonScript = path.join(__dirname, '../scripts/fetch_stock_history.py');
  const pythonProcess = spawn('/opt/homebrew/bin/python3', [pythonScript, ticker, period]);
  
  let output = '';
  let errorOutput = '';
  
  pythonProcess.stdout.on('data', (data) => {
    output += data.toString();
  });
  
  pythonProcess.stderr.on('data', (data) => {
    errorOutput += data.toString();
    console.error(data.toString());
  });
  
  pythonProcess.on('close', (code) => {
    if (code === 0) {
      try {
        const result = JSON.parse(output);
        res.json(result);
      } catch (e) {
        console.error('Failed to parse Python output:', e);
        res.status(500).json({
          success: false,
          error: 'Failed to parse stock data',
          details: e.message
        });
      }
    } else {
      console.error(`Python script exited with code ${code}`);
      res.status(500).json({
        success: false,
        error: `Failed to fetch stock data (exit code ${code})`,
        details: errorOutput
      });
    }
  });
});

// Insider trades endpoint
app.get('/api/insider-trades/:ticker', (req, res) => {
  const ticker = req.params.ticker.toUpperCase();
  const daysBack = req.query.days || 1461; // Default to ~4 years
  
  console.log(`Fetching insider trades for ${ticker}, days back: ${daysBack}`);
  
  const pythonScript = path.join(__dirname, '../scripts/fetch_insider_trades.py');
  const pythonProcess = spawn('/opt/homebrew/bin/python3', [pythonScript, ticker, daysBack]);
  
  let output = '';
  let errorOutput = '';
  
  pythonProcess.stdout.on('data', (data) => {
    output += data.toString();
  });
  
  pythonProcess.stderr.on('data', (data) => {
    errorOutput += data.toString();
    console.error(data.toString());
  });
  
  pythonProcess.on('close', (code) => {
    if (code === 0) {
      try {
        const result = JSON.parse(output);
        res.json(result);
      } catch (e) {
        console.error('Failed to parse Python output:', e);
        res.status(500).json({
          success: false,
          error: 'Failed to parse insider trades data',
          details: e.message
        });
      }
    } else {
      console.error(`Python script exited with code ${code}`);
      res.status(500).json({
        success: false,
        error: `Failed to fetch insider trades (exit code ${code})`,
        details: errorOutput
      });
    }
  });
});

// EDGAR historical data endpoint (extended history beyond 2 years)
app.get('/api/edgar-trades/:ticker', (req, res) => {
  const ticker = req.params.ticker.toUpperCase();
  const maxYears = req.query.years || 5; // Default to 5 years for faster response
  
  console.log(`Fetching EDGAR historical trades for ${ticker}, max years: ${maxYears}`);
  
  const pythonScript = path.join(__dirname, '../scripts/fetch_edgar_trades.py');
  const pythonProcess = spawn('/opt/homebrew/bin/python3', [pythonScript, ticker, maxYears]);
  
  let output = '';
  let errorOutput = '';
  
  pythonProcess.stdout.on('data', (data) => {
    output += data.toString();
  });
  
  pythonProcess.stderr.on('data', (data) => {
    errorOutput += data.toString();
  });
  
  pythonProcess.on('close', (code) => {
    if (code === 0) {
      try {
        const result = JSON.parse(output);
        res.json(result);
      } catch (e) {
        console.error('Failed to parse EDGAR data:', e);
        res.status(500).json({
          success: false,
          error: 'Failed to parse EDGAR historical data',
          details: e.message
        });
      }
    } else {
      console.error(`EDGAR script exited with code ${code}`);
      res.status(500).json({
        success: false,
        error: `Failed to fetch EDGAR data (exit code ${code})`,
        details: errorOutput
      });
    }
  });
});

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: 'Server is running' });
});

// Political trades endpoint - Get paginated/filtered political trades from SQLite
app.get('/api/political-trades', (req, res) => {
  try {
    // Pagination params
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 50;
    const offset = (page - 1) * limit;
    
    // Filter params
    const { 
      ticker,
      politician,
      party,
      chamber,
      trade_type,
      min_amount,
      days
    } = req.query;
    
    // Build query dynamically
    let whereConditions = [];
    let params = [];
    
    if (ticker) {
      whereConditions.push('ticker = ?');
      params.push(ticker.toUpperCase());
    }
    
    if (politician) {
      whereConditions.push('politician LIKE ?');
      params.push(`%${politician}%`);
    }
    
    if (party && party !== 'all') {
      whereConditions.push('party = ?');
      params.push(party);
    }
    
    if (chamber && chamber !== 'all') {
      whereConditions.push('LOWER(source) = ?');
      params.push(chamber.toLowerCase());
    }
    
    if (trade_type && trade_type !== 'all') {
      whereConditions.push('trade_type = ?');
      params.push(trade_type);
    }
    
    if (min_amount) {
      whereConditions.push('amount_value >= ?');
      params.push(parseFloat(min_amount));
    }
    
    if (days) {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - parseInt(days));
      whereConditions.push('trade_date >= ?');
      params.push(cutoffDate.toISOString().split('T')[0]);
    }
    
    const whereClause = whereConditions.length > 0 
      ? 'WHERE ' + whereConditions.join(' AND ')
      : '';
    
    // Get total count
    const countQuery = `SELECT COUNT(*) as total FROM political_trades ${whereClause}`;
    const countResult = db.prepare(countQuery).get(...params);
    const total = countResult.total;
    
    // Get paginated data
    const dataQuery = `
      SELECT * FROM political_trades 
      ${whereClause}
      ORDER BY trade_date DESC
      LIMIT ? OFFSET ?
    `;
    const trades = db.prepare(dataQuery).all(...params, limit, offset);
    
    console.log(`📊 Political trades: page ${page}, ${trades.length} trades (${total} total)`);
    
    res.json({
      success: true,
      trades: trades,
      pagination: {
        page: page,
        limit: limit,
        total: total,
        pages: Math.ceil(total / limit),
        hasMore: page < Math.ceil(total / limit)
      }
    });
  } catch (err) {
    console.error('Error fetching political trades:', err);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch political trades',
      details: err.message
    });
  }
});

// Political trades by ticker endpoint
app.get('/api/political-trades/:ticker', (req, res) => {
  const ticker = req.params.ticker.toUpperCase();
  console.log(`Fetching political trades for ${ticker}`);
  
  const csvPath = path.join(__dirname, '../output CSVs/political_trades_latest.csv');
  
  // Check if file exists
  if (!fs.existsSync(csvPath)) {
    res.json({
      success: true,
      ticker: ticker,
      purchases: [],
      sales: [],
      total_politicians: 0,
      message: 'No political trades data available yet'
    });
    return;
  }
  
  try {
    const csvData = fs.readFileSync(csvPath, 'utf-8');
    const lines = csvData.split('\n');
    const headers = lines[0].split(',');
    
    const purchases = [];
    const sales = [];
    const politicians = new Set();
    
    for (let i = 1; i < lines.length; i++) {
      if (!lines[i].trim()) continue;
      
      const values = lines[i].split(',');
      const tradeTicker = values[2]?.trim().toUpperCase();
      
      if (tradeTicker === ticker) {
        const tradeType = values[4]?.trim();
        const politician = values[1]?.trim();
        const tradeDate = values[5]?.trim();
        const amountRange = values[7]?.trim();
        const amountValue = parseFloat(values[8]) || 0;
        const party = values[9]?.trim();
        const source = values[0]?.trim();
        
        politicians.add(politician);
        
        const trade = {
          politician,
          party,
          source,
          date: tradeDate,
          amount_range: amountRange,
          amount_value: amountValue
        };
        
        if (tradeType === 'Purchase') {
          purchases.push(trade);
        } else {
          sales.push(trade);
        }
      }
    }
    
    res.json({
      success: true,
      ticker: ticker,
      purchases,
      sales,
      total_politicians: politicians.size
    });
  } catch (err) {
    console.error('Error parsing political trades CSV:', err);
    res.status(500).json({
      success: false,
      error: 'Failed to parse political trades data',
      details: err.message
    });
  }
});

// Run political trades scraper endpoint
app.post('/api/scrape-political', (req, res) => {
  const {
    daysBack = 60,
    source = 'both'
  } = req.body;

  console.log('Starting political trades scraper with params:', req.body);

  const pythonScript = path.join(__dirname, '../scripts/fetch_political_trades.py');
  const args = [
    pythonScript,
    '--days', daysBack.toString(),
    '--source', source
  ];

  const pythonProcess = spawn('/opt/homebrew/bin/python3', args);
  
  let output = '';
  let errorOutput = '';

  pythonProcess.stdout.on('data', (data) => {
    const chunk = data.toString();
    output += chunk;
    console.log(chunk);
  });

  pythonProcess.stderr.on('data', (data) => {
    const chunk = data.toString();
    errorOutput += chunk;
    console.error(chunk);
  });

  pythonProcess.on('close', (code) => {
    if (code === 0) {
      console.log('Political trades scraper completed successfully');
      res.json({ 
        success: true, 
        message: 'Political trades data fetched successfully!',
        output: output
      });
    } else {
      console.error(`Political trades scraper exited with code ${code}`);
      res.status(500).json({ 
        success: false, 
        message: `Political trades scraper failed with exit code ${code}`,
        error: errorOutput 
      });
    }
  });
});

// Update political trades database endpoint
app.post('/api/update-political-trades', (req, res) => {
  console.log('🔄 Starting political trades database update...');

  const updateScript = path.join(__dirname, '../scripts/update_political_trades.sh');
  const updateProcess = spawn('bash', [updateScript]);
  
  let output = '';
  let errorOutput = '';

  updateProcess.stdout.on('data', (data) => {
    const chunk = data.toString();
    output += chunk;
    console.log(chunk);
  });

  updateProcess.stderr.on('data', (data) => {
    const chunk = data.toString();
    errorOutput += chunk;
    console.error(chunk);
  });

  updateProcess.on('close', (code) => {
    if (code === 0) {
      console.log('✅ Political trades update completed successfully');
      res.json({ 
        success: true, 
        message: 'Political trades database updated successfully! Refresh to see new data.',
        output: output
      });
    } else {
      console.error(`❌ Update script exited with code ${code}`);
      res.status(500).json({ 
        success: false, 
        message: `Update failed with exit code ${code}`,
        error: errorOutput 
      });
    }
  });
});

// Fetch latest Quiver trades and import to database
app.post('/api/fetch-quiver-trades', (req, res) => {
  console.log('🔥 Fetching latest Quiver political trades...');

  const venvPython = path.join(__dirname, '../.venv/bin/python');
  const fetchScript = path.join(__dirname, '../scripts/fetch_quiver_trades.py');
  const fetchProcess = spawn(venvPython, [fetchScript]);
  
  let output = '';
  let errorOutput = '';

  fetchProcess.stdout.on('data', (data) => {
    const chunk = data.toString();
    output += chunk;
    console.log(chunk);
  });

  fetchProcess.stderr.on('data', (data) => {
    const chunk = data.toString();
    errorOutput += chunk;
    console.error(chunk);
  });

  fetchProcess.on('close', (code) => {
    if (code === 0) {
      console.log('✅ Quiver trades fetched successfully, now importing to database...');
      
      // Import the CSV to database
      const importScript = path.join(__dirname, '../scripts/import_to_db.py');
      const csvPath = path.join(__dirname, '../output CSVs/quiver_trades_current.csv');
      const importProcess = spawn(venvPython, [importScript, csvPath]);
      
      let importOutput = '';
      let importError = '';
      
      importProcess.stdout.on('data', (data) => {
        const chunk = data.toString();
        importOutput += chunk;
        console.log(chunk);
      });
      
      importProcess.stderr.on('data', (data) => {
        const chunk = data.toString();
        importError += chunk;
        console.error(chunk);
      });
      
      importProcess.on('close', (importCode) => {
        if (importCode === 0) {
          console.log('✅ Database updated with Quiver trades');
          res.json({ 
            success: true, 
            message: 'Latest political trades fetched and imported! Refresh to see new data.',
            output: output + '\n' + importOutput
          });
        } else {
          console.error(`❌ Import failed with code ${importCode}`);
          res.status(500).json({ 
            success: false, 
            message: `Data fetched but import failed with exit code ${importCode}`,
            error: importError 
          });
        }
      });
    } else {
      console.error(`❌ Fetch script exited with code ${code}`);
      res.status(500).json({ 
        success: false, 
        message: `Failed to fetch Quiver trades with exit code ${code}`,
        error: errorOutput 
      });
    }
  });
});

// Politician aggregation endpoint for advanced filtering
app.get('/api/politician-stats', (req, res) => {
  try {
    const { 
      minTotalAmount,
      minTradeCount,
      days,
      tradeType  // 'purchase', 'sale', or 'all'
    } = req.query;
    
    // Build WHERE clause for filtering
    let whereConditions = [];
    let params = [];
    
    if (days) {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - parseInt(days));
      whereConditions.push('trade_date >= ?');
      params.push(cutoffDate.toISOString().split('T')[0]);
    }
    
    if (tradeType && tradeType !== 'all') {
      whereConditions.push('LOWER(trade_type) = ?');
      params.push(tradeType.toLowerCase());
    }
    
    const whereClause = whereConditions.length > 0 
      ? 'WHERE ' + whereConditions.join(' AND ')
      : '';
    
    // Aggregate by politician
    const query = `
      SELECT 
        politician,
        party,
        source as chamber,
        COUNT(*) as trade_count,
        SUM(amount_value) as total_amount,
        MIN(trade_date) as earliest_trade,
        MAX(trade_date) as latest_trade,
        GROUP_CONCAT(DISTINCT ticker) as tickers
      FROM political_trades
      ${whereClause}
      GROUP BY politician, party, source
      HAVING 1=1
        ${minTotalAmount ? 'AND total_amount >= ?' : ''}
        ${minTradeCount ? 'AND trade_count >= ?' : ''}
      ORDER BY total_amount DESC
    `;
    
    // Add HAVING clause params
    if (minTotalAmount) params.push(parseFloat(minTotalAmount));
    if (minTradeCount) params.push(parseInt(minTradeCount));
    
    const politicians = db.prepare(query).all(...params);
    
    console.log(`📊 Politician stats: ${politicians.length} politicians match criteria`);
    
    res.json({
      success: true,
      politicians: politicians,
      count: politicians.length
    });
  } catch (err) {
    console.error('Error fetching politician stats:', err);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch politician statistics',
      details: err.message
    });
  }
});

// Endpoint to get top monthly insider trading stocks
app.get('/api/top-monthly-trades', (req, res) => {
  try {
    const jsonPath = path.join(__dirname, '../output CSVs/top_monthly_insider_trades.json');
    
    if (!fs.existsSync(jsonPath)) {
      return res.json({
        success: false,
        message: 'Top monthly trades data not available. Run the scraper first.'
      });
    }
    
    const data = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
    
    res.json({
      success: true,
      ...data
    });
  } catch (err) {
    console.error('Error reading top monthly trades:', err);
    res.status(500).json({
      success: false,
      error: 'Failed to load top monthly trades data',
      details: err.message
    });
  }
});

// Endpoint to run the live EDGAR purchases scraper
app.post('/api/scrape-live-purchases', (req, res) => {
  console.log('Starting live EDGAR purchases scraper...');
  
  const daysBack = req.body.days || 1; // Default to last 2 days
  const pythonScript = path.join(__dirname, '../scripts/fetch_live_edgar_purchases.py');
  const pythonPath = path.join(__dirname, '../.venv/bin/python');
  const pythonProcess = spawn(pythonPath, [pythonScript, '--days', daysBack.toString()]);
  
  let output = '';
  let errorOutput = '';
  
  pythonProcess.stdout.on('data', (data) => {
    const chunk = data.toString();
    output += chunk;
    console.log(chunk);
  });
  
  pythonProcess.stderr.on('data', (data) => {
    const chunk = data.toString();
    errorOutput += chunk;
    console.error(chunk);
  });
  
  pythonProcess.on('close', (code) => {
    if (code === 0) {
      try {
        const result = JSON.parse(output);
        console.log('Live purchases scraper completed successfully');
        
        // Save to public folder for caching
        const destJSON = path.join(__dirname, 'public/live_edgar_purchases.json');
        fs.writeFile(destJSON, output, (err) => {
          if (err) {
            console.error('Error saving live purchases JSON:', err);
          } else {
            console.log('Live purchases JSON saved to public folder');
          }
        });
        
        res.json(result);
      } catch (e) {
        console.error('Failed to parse live purchases output:', e);
        res.status(500).json({
          success: false,
          message: 'Scraper completed but failed to parse output',
          error: e.message,
          raw: output
        });
      }
    } else {
      console.error('Live purchases scraper failed with code', code);
      res.status(500).json({
        success: false,
        message: 'Scraper failed',
        error: errorOutput || output
      });
    }
  });
});

// Endpoint to get cached live purchases data
app.get('/api/live-purchases', (req, res) => {
  const jsonPath = path.join(__dirname, 'public/live_edgar_purchases.json');
  
  fs.readFile(jsonPath, 'utf8', (err, data) => {
    if (err) {
      console.error('No cached live purchases data found');
      res.json({
        success: false,
        message: 'No data available. Click "Update Live Purchases" to fetch.',
        companies: []
      });
    } else {
      try {
        const result = JSON.parse(data);
        res.json(result);
      } catch (e) {
        console.error('Failed to parse cached live purchases:', e);
        res.status(500).json({
          success: false,
          message: 'Failed to parse cached data',
          error: e.message
        });
      }
    }
  });
});

// Endpoint to run the top monthly trades scraper
app.post('/api/scrape-top-monthly', (req, res) => {
  console.log('Starting top monthly trades scraper...');
  
  const pythonScript = path.join(__dirname, '../scripts/fetch_top_monthly_insider_trades.py');
  const pythonProcess = spawn('/opt/homebrew/bin/python3', [pythonScript]);
  
  let output = '';
  let errorOutput = '';
  
  pythonProcess.stdout.on('data', (data) => {
    const chunk = data.toString();
    output += chunk;
    console.log(chunk);
  });
  
  pythonProcess.stderr.on('data', (data) => {
    const chunk = data.toString();
    errorOutput += chunk;
    console.error(chunk);
  });
  
  pythonProcess.on('close', (code) => {
    if (code === 0) {
      console.log('Top monthly trades scraper completed successfully');
      
      // Copy JSON to public folder for direct access
      const sourceJSON = path.join(__dirname, '../output CSVs/top_monthly_insider_trades.json');
      const destJSON = path.join(__dirname, 'public/top_monthly_insider_trades.json');
      
      fs.copyFile(sourceJSON, destJSON, (err) => {
        if (err) {
          console.error('Error copying JSON:', err);
          res.status(500).json({
            success: false,
            message: 'Scraper completed but failed to copy JSON',
            error: err.message
          });
        } else {
          console.log('JSON copied to public folder');
          res.json({
            success: true,
            message: 'Top monthly trades data updated successfully!',
            output: output
          });
        }
      });
    } else {
      console.error('Scraper failed with code', code);
      res.status(500).json({
        success: false,
        message: 'Scraper failed',
        error: errorOutput || output
      });
    }
  });
});

app.listen(PORT, () => {
  console.log(`Backend server running on http://localhost:${PORT}`);
});
