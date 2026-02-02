#!/usr/bin/env python3
"""
Import Political Trades CSV to SQLite Database
This creates a lightweight database for efficient querying with pagination
"""

import sqlite3
import csv
import os
from datetime import datetime

class PoliticalTradesDB:
    def __init__(self, db_path='../webapp-stocks/political_trades.db'):
        """Initialize database connection"""
        self.db_path = os.path.join(os.path.dirname(__file__), db_path)
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Connect to SQLite database"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        print(f"✅ Connected to database: {self.db_path}")
        
    def create_tables(self):
        """Create tables if they don't exist"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS political_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                politician TEXT NOT NULL,
                ticker TEXT NOT NULL,
                asset_description TEXT,
                trade_type TEXT,
                trade_date TEXT,
                disclosure_date TEXT,
                amount_range TEXT,
                amount_value REAL,
                party TEXT,
                state TEXT,
                district TEXT,
                committee TEXT,
                ptr_link TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for common queries
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_ticker 
            ON political_trades(ticker)
        ''')
        
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_trade_date 
            ON political_trades(trade_date DESC)
        ''')
        
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_party 
            ON political_trades(party)
        ''')
        
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_chamber 
            ON political_trades(source)
        ''')
        
        self.conn.commit()
        print("✅ Tables and indexes created")
        
    def clear_trades(self):
        """Clear existing trades (for fresh import)"""
        self.cursor.execute('DELETE FROM political_trades')
        self.conn.commit()
        print("🗑️  Cleared existing trades")
        
    def import_from_csv(self, csv_path):
        """Import trades from CSV file"""
        csv_path = os.path.join(os.path.dirname(__file__), csv_path)
        
        if not os.path.exists(csv_path):
            print(f"❌ CSV file not found: {csv_path}")
            return False
            
        print(f"📂 Reading CSV: {csv_path}")
        
        trades_imported = 0
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Skip rows with missing required fields
                if not row.get('ticker') or not row.get('politician'):
                    continue
                    
                self.cursor.execute('''
                    INSERT INTO political_trades (
                        source, politician, ticker, asset_description, trade_type,
                        trade_date, disclosure_date, amount_range, amount_value,
                        party, state, district, committee, ptr_link
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row.get('source', ''),
                    row.get('politician', ''),
                    row.get('ticker', ''),
                    row.get('asset_description', ''),
                    row.get('trade_type', ''),
                    row.get('trade_date', ''),
                    row.get('disclosure_date', ''),
                    row.get('amount_range', ''),
                    float(row.get('amount_value', 0) or 0),
                    row.get('party', ''),
                    row.get('state', ''),
                    row.get('district', ''),
                    row.get('committee', ''),
                    row.get('ptr_link', '')
                ))
                
                trades_imported += 1
                
                if trades_imported % 1000 == 0:
                    print(f"  📊 Imported {trades_imported} trades...")
        
        self.conn.commit()
        print(f"✅ Successfully imported {trades_imported} trades")
        return True
        
    def get_stats(self):
        """Get database statistics"""
        self.cursor.execute('SELECT COUNT(*) FROM political_trades')
        total = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT COUNT(DISTINCT ticker) FROM political_trades')
        unique_tickers = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT COUNT(DISTINCT politician) FROM political_trades')
        unique_politicians = self.cursor.fetchone()[0]
        
        self.cursor.execute('''
            SELECT party, COUNT(*) 
            FROM political_trades 
            WHERE party != '' 
            GROUP BY party
        ''')
        party_stats = self.cursor.fetchall()
        
        return {
            'total_trades': total,
            'unique_tickers': unique_tickers,
            'unique_politicians': unique_politicians,
            'party_breakdown': dict(party_stats)
        }
        
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("🔒 Database connection closed")

def main():
    print("=" * 70)
    print("🏛️  Political Trades Database Importer")
    print("=" * 70)
    
    db = PoliticalTradesDB()
    db.connect()
    db.create_tables()
    
    # Clear existing data
    db.clear_trades()
    
    # Import from CSV
    success = db.import_from_csv('../output CSVs/political_trades_latest.csv')
    
    if success:
        # Show stats
        stats = db.get_stats()
        print("\n📊 Database Statistics:")
        print(f"   Total Trades: {stats['total_trades']}")
        print(f"   Unique Tickers: {stats['unique_tickers']}")
        print(f"   Unique Politicians: {stats['unique_politicians']}")
        print(f"   Party Breakdown:")
        for party, count in stats['party_breakdown'].items():
            print(f"      {party}: {count}")
        
        print(f"\n✅ Database ready at: {db.db_path}")
        print(f"   Size: {os.path.getsize(db.db_path) / 1024:.1f} KB")
    
    db.close()
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
