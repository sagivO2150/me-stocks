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

// EDGAR historical data endpoint with Server-Sent Events for progress (extended history beyond 2 years)
app.get('/api/edgar-trades/:ticker', (req, res) => {
  const ticker = req.params.ticker.toUpperCase();
  const maxYears = 5; // ALWAYS fetch 5 years of data
  
  console.log(`Fetching EDGAR historical trades for ${ticker}, max years: ${maxYears}`);
  
  // Set up Server-Sent Events
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();
  
  const pythonScript = path.join(__dirname, '../scripts/fetch_edgar_trades.py');
  const pythonPath = path.join(__dirname, '../.venv/bin/python');
  const pythonProcess = spawn(pythonPath, [pythonScript, ticker, maxYears]);
  
  let output = '';
  let errorOutput = '';
  
  pythonProcess.stdout.on('data', (data) => {
    output += data.toString();
  });
  
  pythonProcess.stderr.on('data', (data) => {
    const chunk = data.toString();
    errorOutput += chunk;
    
    // Parse progress messages and send as SSE
    const lines = chunk.split('\n');
    for (const line of lines) {
      // Match progress patterns like "Progress: 10/439, found 0 transactions so far"
      const progressMatch = line.match(/Progress: (\d+)\/(\d+), found (\d+) transactions/);
      if (progressMatch) {
        const [, current, total, found] = progressMatch;
        res.write(`data: ${JSON.stringify({
          type: 'progress',
          current: parseInt(current),
          total: parseInt(total),
          found: parseInt(found)
        })}\n\n`);
      }
      
      // Match other status messages
      if (line.includes('Fetching Form 4 filings') || line.includes('Processing') || line.includes('Found')) {
        res.write(`data: ${JSON.stringify({
          type: 'status',
          message: line.trim()
        })}\n\n`);
      }
    }
  });
  
  pythonProcess.on('close', (code) => {
    if (code === 0) {
      try {
        const result = JSON.parse(output);
        res.write(`data: ${JSON.stringify({
          type: 'complete',
          data: result
        })}\n\n`);
      } catch (e) {
        console.error('Failed to parse EDGAR data:', e);
        res.write(`data: ${JSON.stringify({
          type: 'error',
          error: 'Failed to parse EDGAR historical data',
          details: e.message
        })}\n\n`);
      }
    } else {
      console.error(`EDGAR script exited with code ${code}`);
      res.write(`data: ${JSON.stringify({
        type: 'error',
        error: `Failed to fetch EDGAR data (exit code ${code})`,
        details: errorOutput
      })}\n\n`);
    }
    res.end();
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
    // Read from public folder which has the enriched data with eventClassification
    const jsonPath = path.join(__dirname, 'public/top_monthly_insider_trades.json');
    
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
      
      fs.copyFile(sourceJSON, destJSON, async (err) => {
        if (err) {
          console.error('Error copying JSON:', err);
          res.status(500).json({
            success: false,
            message: 'Scraper completed but failed to copy JSON',
            error: err.message
          });
        } else {
          console.log('JSON copied to public folder');
          
          // Now enrich with event classification
          try {
            console.log('Adding event classification to monthly data...');
            const jsonData = JSON.parse(fs.readFileSync(destJSON, 'utf8'));
            
            // The JSON has a "data" array containing the stocks
            if (!jsonData.data || !Array.isArray(jsonData.data)) {
              throw new Error('Invalid JSON structure - expected data array');
            }
            
            // Process stocks in parallel batches of 10 for speed
            const BATCH_SIZE = 10;
            const stocks = jsonData.data;
            console.log(`Processing ${stocks.length} stocks in batches of ${BATCH_SIZE}...`);
            
            for (let i = 0; i < stocks.length; i += BATCH_SIZE) {
              const batch = stocks.slice(i, i + BATCH_SIZE);
              const batchNum = Math.floor(i / BATCH_SIZE) + 1;
              const totalBatches = Math.ceil(stocks.length / BATCH_SIZE);
              
              console.log(`\nBatch ${batchNum}/${totalBatches}: Processing ${batch.map(s => s.ticker).join(', ')}`);
              
              // Process this batch in parallel
              await Promise.all(batch.map(async (stock) => {
                try {
                  const events = await classifyEventForStock(stock.ticker);
                  stock.eventClassification = events;
                  if (events && events.length > 0) {
                    const summary = events.map(e => `${e.count} ${e.type}`).join(', ');
                    console.log(`✓ ${stock.ticker}: ${summary}`);
                  } else {
                    console.log(`- ${stock.ticker}: No events`);
                  }
                } catch (e) {
                  console.log(`✗ ${stock.ticker}: Error - ${e.message}`);
                  stock.eventClassification = [];
                }
              }));
            }
            
            // Save enriched data
            console.log('About to save enriched data...');
            console.log('Sample stock before save:', JSON.stringify(jsonData.data[0], null, 2));
            fs.writeFileSync(destJSON, JSON.stringify(jsonData, null, 2));
            console.log('✅ Successfully saved enriched data to:', destJSON);
            console.log('Event classification complete!');
            
            res.json({
              success: true,
              message: 'Top monthly trades data updated successfully with event classification!',
              output: output
            });
          } catch (enrichErr) {
            console.error('Error enriching with events:', enrichErr);
            // Still return success since scraper worked
            res.json({
              success: true,
              message: 'Top monthly trades data updated (event classification failed)',
              output: output
            });
          }
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

// Helper function to classify events for a stock with timeout
async function classifyEventForStock(ticker) {
  const TIMEOUT_MS = 10000; // 10 second timeout per stock
  
  const fetchWithTimeout = async (url, timeoutMs) => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    
    try {
      const response = await fetch(url, { signal: controller.signal });
      clearTimeout(timeout);
      return response;
    } catch (error) {
      clearTimeout(timeout);
      throw error;
    }
  };
  
  try {
    // Fetch both insider trades and stock history in parallel
    const [insiderResponse, historyResponse] = await Promise.all([
      fetchWithTimeout(`http://localhost:${PORT}/api/insider-trades/${ticker}`, TIMEOUT_MS),
      fetchWithTimeout(`http://localhost:${PORT}/api/stock-history/${ticker}?period=2y`, TIMEOUT_MS)
    ]);
    
    if (!insiderResponse.ok) {
      return [];
    }
    
    const insiderData = await insiderResponse.json();
    if (!insiderData.success || !insiderData.purchases || insiderData.purchases.length === 0) {
      return [];
    }
    
    const historyData = await historyResponse.json();
    
    if (!historyResponse.ok || !historyData.success || !historyData.history || historyData.history.length === 0) {
      return [];
    }
    
    // Classify ALL events
    return classifyAllEvents(insiderData, historyData);
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log(`✗ ${ticker}: Timeout (>10s)`);
    } else {
      console.log(`✗ ${ticker}: ${error.message}`);
    }
    return [];
  }
}

// Event classification endpoint - now just reads from stored data
app.get('/api/event-classification/:ticker', async (req, res) => {
  const { ticker } = req.params;
  
  try {
    // Fetch insider trades
    const insiderResponse = await fetch(`http://localhost:${PORT}/api/insider-trades/${ticker}`);
    if (!insiderResponse.ok) {
      return res.json({ success: false, message: 'No insider data' });
    }
    const insiderData = await insiderResponse.json();
    
    if (!insiderData.success || !insiderData.purchases || insiderData.purchases.length === 0) {
      return res.json({ success: false, message: 'No insider purchases' });
    }
    
    // Fetch stock history
    const historyResponse = await fetch(`http://localhost:${PORT}/api/stock-history/${ticker}?period=1y`);
    const historyData = await historyResponse.json();
    
    // If no stock history, we can't classify events properly
    if (!historyResponse.ok || !historyData.success || !historyData.history || historyData.history.length === 0) {
      return res.json({ success: false, message: 'No stock history available' });
    }
    
    // Classify events (simplified version for card display)
    const event = classifyPrimaryEvent(insiderData, historyData);
    
    res.json({
      success: true,
      primaryEvent: event
    });
  } catch (error) {
    console.error('Event classification error:', error);
    res.json({ success: false, message: error.message });
  }
});

function classifyAllEvents(insiderData, historyData) {
  const purchases = insiderData.purchases;
  const history = historyData.history;
  const events = [];
  if (!Array.isArray(purchases) || purchases.length === 0 || !Array.isArray(history) || history.length === 0) {
    return events;
  }
  
  // Group purchases by date
  const purchasesByDate = {};
  purchases.forEach(trade => {
    const dateKey = trade.date.split('T')[0];
    if (!purchasesByDate[dateKey]) {
      purchasesByDate[dateKey] = { trades: [], totalValue: 0 };
    }
    purchasesByDate[dateKey].trades.push(trade);
    purchasesByDate[dateKey].totalValue += trade.value;
  });
  
  const sortedDates = Object.keys(purchasesByDate).sort();
  
  // Price lookup
  const priceByDate = {};
  history.forEach(point => {
    const dateKey = point.date.split('T')[0].split(' ')[0];
    if (!priceByDate[dateKey]) {
      priceByDate[dateKey] = parseFloat(point.close);
    }
  });
  
  const getPriceAt = (dateStr) => priceByDate[dateStr];
  const getPriceOffset = (dateStr, dayOffset) => {
    const date = new Date(dateStr);
    date.setDate(date.getDate() + dayOffset);
    let checkDate = date.toISOString().split('T')[0];
    for (let i = 0; i < 5; i++) {
      if (priceByDate[checkDate]) return priceByDate[checkDate];
      date.setDate(date.getDate() + (dayOffset > 0 ? 1 : -1));
      checkDate = date.toISOString().split('T')[0];
    }
    return null;
  };
  
  const campaignGapDays = 7;
  const campaigns = [];
  let currentCampaign = null;

  sortedDates.forEach((dateStr) => {
    if (!currentCampaign) {
      currentCampaign = {
        startDate: dateStr,
        endDate: dateStr,
        dates: [dateStr],
        totalValue: purchasesByDate[dateStr].totalValue,
        tradeCount: purchasesByDate[dateStr].trades.length
      };
      return;
    }

    const gapDays = (new Date(dateStr) - new Date(currentCampaign.endDate)) / (1000 * 60 * 60 * 24);
    if (gapDays <= campaignGapDays) {
      currentCampaign.endDate = dateStr;
      currentCampaign.dates.push(dateStr);
      currentCampaign.totalValue += purchasesByDate[dateStr].totalValue;
      currentCampaign.tradeCount += purchasesByDate[dateStr].trades.length;
    } else {
      campaigns.push(currentCampaign);
      currentCampaign = {
        startDate: dateStr,
        endDate: dateStr,
        dates: [dateStr],
        totalValue: purchasesByDate[dateStr].totalValue,
        tradeCount: purchasesByDate[dateStr].trades.length
      };
    }
  });

  if (currentCampaign) {
    campaigns.push(currentCampaign);
  }

  const lastHistoryDate = history.length > 0 ? history[history.length - 1].date.split('T')[0].split(' ')[0] : null;
  const latestPriceDate = lastHistoryDate ? new Date(lastHistoryDate) : null;

  campaigns.forEach((campaign) => {
    const startPrice = getPriceAt(campaign.startDate);
    const endPrice = getPriceAt(campaign.endDate) || startPrice;
    const price30Before = getPriceOffset(campaign.startDate, -30);
    const price10After = getPriceOffset(campaign.endDate, 10);
    const price20After = getPriceOffset(campaign.endDate, 20);
    const price5After = getPriceOffset(campaign.endDate, 5);

    const preTrendPct = startPrice && price30Before ? ((startPrice - price30Before) / price30Before) * 100 : null;
    const postTrend10Pct = endPrice && price10After ? ((price10After - endPrice) / endPrice) * 100 : null;
    const postTrend20Pct = endPrice && price20After ? ((price20After - endPrice) / endPrice) * 100 : null;
    const postTrend5Pct = endPrice && price5After ? ((price5After - endPrice) / endPrice) * 100 : null;

    const daysSinceCampaign = latestPriceDate
      ? (latestPriceDate - new Date(campaign.endDate)) / (1000 * 60 * 60 * 24)
      : 0;

    let type = 'stabilizing-accumulation';

    if (!startPrice || !endPrice || daysSinceCampaign < 6 || postTrend5Pct === null) {
      type = 'needs-follow-through';
    } else if (preTrendPct !== null && preTrendPct <= -15 && postTrend10Pct !== null && postTrend10Pct >= 8) {
      type = 'bottom-fishing-win';
    } else if (postTrend10Pct !== null && postTrend10Pct >= 8) {
      type = 'breakout-accumulation';
    } else if (postTrend10Pct !== null && postTrend10Pct <= -8) {
      type = 'failed-support';
    } else if (preTrendPct !== null && preTrendPct >= 10 && postTrend10Pct !== null && postTrend10Pct < 0) {
      type = 'late-chase';
    } else if (postTrend20Pct !== null && postTrend20Pct > 5) {
      type = 'slow-burn-accumulation';
    }

    events.push({
      type,
      count: 1,
      date: campaign.startDate,
      campaignDates: campaign.dates, // All purchase dates in this campaign
      metadata: {
        startDate: campaign.startDate,
        endDate: campaign.endDate,
        totalValue: campaign.totalValue,
        tradeCount: campaign.tradeCount,
        preTrendPct,
        postTrend10Pct,
        postTrend20Pct
      }
    });
  });
  
  // Aggregate by type and collect dates with campaign info
  const aggregated = {};
  events.forEach(e => {
    if (!aggregated[e.type]) {
      aggregated[e.type] = { count: 0, dates: [], campaigns: [] };
    }
    aggregated[e.type].count += 1;
    aggregated[e.type].dates.push(e.date);
    aggregated[e.type].campaigns.push({
      startDate: e.date,
      allDates: e.campaignDates // All purchase dates in this campaign
    });
  });
  
  // Convert to array
  return Object.keys(aggregated).map(type => ({
    type,
    count: aggregated[type].count,
    dates: aggregated[type].dates,
    campaigns: aggregated[type].campaigns
  }));
}

// Keep old function for backward compatibility
function classifyPrimaryEvent(insiderData, historyData) {
  const allEvents = classifyAllEvents(insiderData, historyData);
  if (allEvents.length === 0) return null;
  
  // Return the "best" event as primary
  const priority = [
    'bottom-fishing-win',
    'breakout-accumulation',
    'slow-burn-accumulation',
    'stabilizing-accumulation',
    'needs-follow-through',
    'late-chase',
    'failed-support'
  ];
  for (const eventType of priority) {
    const found = allEvents.find(e => e.type === eventType);
    if (found) {
      const labels = {
        'bottom-fishing-win': { label: 'Bottom Catch', icon: '🎯', colorClass: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', tooltip: 'Bought deep drawdown and got a fast rebound.' },
        'breakout-accumulation': { label: 'Breakout Build', icon: '🚀', colorClass: 'bg-purple-500/20 text-purple-400 border-purple-500/30', tooltip: 'Insiders accumulated ahead of a breakout.' },
        'slow-burn-accumulation': { label: 'Slow Burn', icon: '🟢', colorClass: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30', tooltip: 'Not instant, but trended up over ~20 days.' },
        'stabilizing-accumulation': { label: 'Stabilizing', icon: '🧱', colorClass: 'bg-blue-500/20 text-blue-400 border-blue-500/30', tooltip: 'Buying likely supported price without clear breakout.' },
        'needs-follow-through': { label: 'Pending', icon: '⏳', colorClass: 'bg-slate-500/20 text-slate-300 border-slate-500/30', tooltip: 'Too recent or too little data to score yet.' },
        'late-chase': { label: 'Late Chase', icon: '⚠️', colorClass: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30', tooltip: 'Insiders bought after run-up and momentum faded.' },
        'failed-support': { label: 'Failed Support', icon: '❌', colorClass: 'bg-red-500/20 text-red-400 border-red-500/30', tooltip: 'Buying did not prevent a post-trade drop.' }
      };
      return labels[eventType];
    }
  }
  
  return null;
}

app.listen(PORT, () => {
  console.log(`Backend server running on http://localhost:${PORT}`);
});
