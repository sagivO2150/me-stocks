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
  const events = []; // Now each event will have: { type, count, dates: [] }
  
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
  
  // Helper to check if date is within 7 business days
  const isWithin7BusinessDays = (date1, date2) => {
    const d1 = new Date(date1);
    const d2 = new Date(date2);
    let businessDays = 0;
    let current = new Date(d1);
    
    while (current <= d2 && businessDays <= 7) {
      const dayOfWeek = current.getDay();
      if (dayOfWeek !== 0 && dayOfWeek !== 6) { // Not weekend
        businessDays++;
      }
      current.setDate(current.getDate() + 1);
    }
    
    return businessDays <= 7;
  };
  
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
  
  // Analyze each purchase or cluster of purchases
  const analyzed = new Set(); // Track which dates we've already analyzed
  
  for (let i = 0; i < sortedDates.length; i++) {
    if (analyzed.has(i)) continue;
    
    const currentDate = sortedDates[i];
    const priceAtPurchase = getPriceAt(currentDate);
    if (!priceAtPurchase) continue;
    
    // Check if this purchase is part of a clamp (multiple purchases within 7 days)
    // We'll classify each purchase individually, but note if it's part of a clamp pattern
    let isPartOfClamp = false;
    let clampDates = [currentDate];
    
    // Look ahead to see if there are more purchases within 7 days
    for (let j = i + 1; j < sortedDates.length; j++) {
      const daysDiff = (new Date(sortedDates[j]) - new Date(currentDate)) / (1000 * 60 * 60 * 24);
      if (daysDiff <= 7) {
        isPartOfClamp = true;
        clampDates.push(sortedDates[j]);
      } else {
        break;
      }
    }
    
    // Also check if previous purchase was within 7 days (this purchase is part of ongoing clamp)
    if (i > 0 && !analyzed.has(i - 1)) {
      const daysSincePrev = (new Date(currentDate) - new Date(sortedDates[i - 1])) / (1000 * 60 * 60 * 24);
      if (daysSincePrev <= 7) {
        isPartOfClamp = true;
      }
    }
    
    // Now classify THIS INDIVIDUAL PURCHASE
    const daysSince = (new Date() - new Date(currentDate)) / (1000 * 60 * 60 * 24);
    const price3After = getPriceOffset(currentDate, 7); // Check 7 days after for clamp events
    const price30Before = getPriceOffset(currentDate, -30);
    const price5Before = getPriceOffset(currentDate, -5);
    
    // If part of a clamp, check if it worked out
    if (isPartOfClamp && price3After && daysSince > 7) {
      const pctChange = ((price3After - priceAtPurchase) / priceAtPurchase) * 100;
      const price30BeforeClamp = getPriceOffset(currentDate, -30);
      const wasInSlump = price30BeforeClamp && (price30BeforeClamp > priceAtPurchase * 1.15);
      
      if (pctChange >= 10) {
        events.push({ 
          type: wasInSlump ? 'slump-recovery' : 'holy-grail', 
          count: 1, 
          date: currentDate 
        });
      } else if (daysSince < 7) {
        events.push({ type: 'clamp', count: 1, date: currentDate });
      } else {
        events.push({ type: 'disqualified', count: 1, date: currentDate });
      }
      analyzed.add(i);
      continue;
    }
    
    // If part of clamp but too recent
    if (isPartOfClamp && daysSince <= 7) {
      events.push({ type: 'clamp', count: 1, date: currentDate });
      analyzed.add(i);
      continue;
    }
    
    // Single purchase (not part of clamp) - check event type
    const price1Before = getPriceOffset(currentDate, -1);
    const price3AfterSingle = getPriceOffset(currentDate, 3);
    
    // Check for plateau: stable 5 days before (<5% change) + price up after 3 days
    if (price5Before && price1Before && priceAtPurchase && price3AfterSingle && daysSince > 3) {
      const priceChangeBefore = Math.abs((priceAtPurchase - price5Before) / price5Before) * 100;
      const priceChangeAfter3Days = ((price3AfterSingle - priceAtPurchase) / priceAtPurchase) * 100;
      
      // Plateau: stable period before (<5% change) and went up after 3 days
      if (priceChangeBefore < 5 && priceChangeAfter3Days > 0) {
        // Check if there's a follow-up event within 7 business days
        let hasFollowUpEvent = false;
        for (let j = i + 1; j < sortedDates.length; j++) {
          if (isWithin7BusinessDays(currentDate, sortedDates[j])) {
            hasFollowUpEvent = true;
            break;
          }
        }
        
        if (hasFollowUpEvent) {
          // Plateau with follow-up = valid plateau
          events.push({ type: 'plateau', count: 1, date: currentDate });
          analyzed.add(i);
          continue;
        } else {
          // Plateau without follow-up = disqualified
          events.push({ type: 'disqualified', count: 1, date: currentDate });
          analyzed.add(i);
          continue;
        }
      }
    }
    
    // Check for mid-rise (10-30% uptrend in 30 days before)
    if (price30Before && priceAtPurchase) {
      const priceRise = ((priceAtPurchase - price30Before) / price30Before) * 100;
      if (priceRise >= 10 && priceRise < 30) {
        events.push({ type: 'mid-rise', count: 1, date: currentDate });
        analyzed.add(i);
        continue; // Skip to next purchase
      }
    }
    
    // Check if single purchase is disqualified (price down after 3 days)
    if (price3AfterSingle && priceAtPurchase && daysSince > 3) {
      const pctChange = ((price3AfterSingle - priceAtPurchase) / priceAtPurchase) * 100;
      if (pctChange < 0) {
        events.push({ type: 'disqualified', count: 1, date: currentDate });
        analyzed.add(i);
        continue;
      }
      
      // If price stayed flat or went up slightly (but not plateau criteria), classify as plateau
      if (pctChange >= 0) {
        events.push({ type: 'plateau', count: 1, date: currentDate });
        analyzed.add(i);
        continue;
      }
    }
    
    // If too recent (< 3 days), classify as clamp (single purchase, waiting to see outcome)
    if (daysSince <= 3) {
      events.push({ type: 'clamp', count: 1, date: currentDate });
      analyzed.add(i);
      continue;
    }
    
    // Default: if we have no price data or can't classify, mark as plateau (neutral)
    events.push({ type: 'plateau', count: 1, date: currentDate });
    analyzed.add(i);
  }
  
  // Check for restock pattern (3+ purchases within 30 days that aren't clamps)
  // Only count dates that haven't been analyzed yet
  for (let i = 0; i <= sortedDates.length - 3; i++) {
    // Skip if this date was already analyzed
    if (analyzed.has(i)) continue;
    
    const span = (new Date(sortedDates[i + 2]) - new Date(sortedDates[i])) / (1000 * 60 * 60 * 24);
    if (span <= 30) {
      // Make sure it's not a clamp
      let isClamp = true;
      for (let j = i; j < i + 2; j++) {
        const gap = (new Date(sortedDates[j + 1]) - new Date(sortedDates[j])) / (1000 * 60 * 60 * 24);
        if (gap > 7) {
          isClamp = false;
          break;
        }
      }
      if (!isClamp) {
        events.push({ type: 'restock', count: 1, date: sortedDates[i] });
        break; // Only count once
      }
    }
  }
  
  // Aggregate by type and collect dates
  const aggregated = {};
  events.forEach(e => {
    if (!aggregated[e.type]) {
      aggregated[e.type] = { count: 0, dates: [] };
    }
    aggregated[e.type].count += 1;
    aggregated[e.type].dates.push(e.date);
  });
  
  // Convert to array
  return Object.keys(aggregated).map(type => ({
    type,
    count: aggregated[type].count,
    dates: aggregated[type].dates
  }));
}

// Keep old function for backward compatibility
function classifyPrimaryEvent(insiderData, historyData) {
  const allEvents = classifyAllEvents(insiderData, historyData);
  if (allEvents.length === 0) return null;
  
  // Return the "best" event as primary
  const priority = ['holy-grail', 'slump-recovery', 'clamp', 'restock', 'mid-rise', 'disqualified'];
  for (const eventType of priority) {
    const found = allEvents.find(e => e.type === eventType);
    if (found) {
      const labels = {
        'holy-grail': { label: 'Holy Grail', icon: '🔥', colorClass: 'bg-purple-500/20 text-purple-400 border-purple-500/30', tooltip: 'Insider clamp + price up!' },
        'slump-recovery': { label: 'Slump Recovery', icon: '📈', colorClass: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', tooltip: 'Bottom-fishing success!' },
        'clamp': { label: 'Clamp Event', icon: '📊', colorClass: 'bg-blue-500/20 text-blue-400 border-blue-500/30', tooltip: 'Purchases within 7 days' },
        'restock': { label: 'Restock', icon: '🔄', colorClass: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30', tooltip: '3+ purchases in 30 days' },
        'mid-rise': { label: 'Mid-Rise', icon: '⚠️', colorClass: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30', tooltip: 'Buying during uptrend' },
        'disqualified': { label: 'Disqualified', icon: '❌', colorClass: 'bg-red-500/20 text-red-400 border-red-500/30', tooltip: "Didn't work out" }
      };
      return labels[eventType];
    }
  }
  
  return null;
}

app.listen(PORT, () => {
  console.log(`Backend server running on http://localhost:${PORT}`);
});
