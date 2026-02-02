import express from 'express';
import { spawn } from 'child_process';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

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

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: 'Server is running' });
});

// Political trades endpoint - Get all political trades
app.get('/api/political-trades', (req, res) => {
  console.log('Fetching all political trades from CSV');
  
  const csvPath = path.join(__dirname, '../output CSVs/political_trades_latest.csv');
  
  // Check if file exists
  if (!fs.existsSync(csvPath)) {
    res.status(404).json({
      success: false,
      error: 'Political trades data not found. Run the political trades scraper first.'
    });
    return;
  }
  
  try {
    const csvData = fs.readFileSync(csvPath, 'utf-8');
    const lines = csvData.trim().split('\n');
    
    // Parse CSV properly handling quoted fields with commas
    const parseCSVLine = (line) => {
      const result = [];
      let current = '';
      let inQuotes = false;
      
      for (let i = 0; i < line.length; i++) {
        const char = line[i];
        if (char === '"') {
          inQuotes = !inQuotes;
        } else if (char === ',' && !inQuotes) {
          result.push(current.trim());
          current = '';
        } else {
          current += char;
        }
      }
      result.push(current.trim());
      return result;
    };
    
    const headers = parseCSVLine(lines[0]);
    const trades = [];
    
    for (let i = 1; i < lines.length; i++) {
      if (lines[i].trim()) {
        const values = parseCSVLine(lines[i]);
        const trade = {};
        headers.forEach((header, idx) => {
          trade[header] = values[idx] || '';
        });
        trades.push(trade);
      }
    }
    
    res.json({
      success: true,
      trades: trades,
      total: trades.length
    });
  } catch (err) {
    console.error('Error reading political trades CSV:', err);
    res.status(500).json({
      success: false,
      error: 'Failed to read political trades data',
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

app.listen(PORT, () => {
  console.log(`Backend server running on http://localhost:${PORT}`);
});
