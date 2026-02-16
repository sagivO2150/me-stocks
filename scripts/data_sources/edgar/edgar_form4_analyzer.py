#!/usr/bin/env python3
"""
Deep dive into EDGAR Form 4 to see what data we can extract beyond OpenInsider
"""
import requests
from bs4 import BeautifulSoup
import json
import xml.etree.ElementTree as ET
from datetime import datetime

def get_form4_xml_url(filing_index_url):
    """Extract the XML file URL from the filing index page"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }
    
    response = requests.get(filing_index_url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the .xml file link in the document table
    table = soup.find('table', {'class': 'tableFile'})
    if not table:
        return None
    
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) >= 3:
            doc_type = cols[3].text.strip() if len(cols) > 3 else cols[0].text.strip()
            if 'primary_doc.xml' in doc_type or doc_type.endswith('.xml'):
                link = cols[2].find('a')
                if link:
                    return 'https://www.sec.gov' + link['href']
    
    return None


def parse_form4_xml(xml_url):
    """Parse Form 4 XML and extract all available data"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }
    
    response = requests.get(xml_url, headers=headers, timeout=30)
    
    # Parse XML
    root = ET.fromstring(response.content)
    
    # Extract issuer info
    issuer = root.find('.//issuer')
    issuer_name = issuer.find('issuerName').text if issuer is not None and issuer.find('issuerName') is not None else 'N/A'
    issuer_cik = issuer.find('issuerCik').text if issuer is not None and issuer.find('issuerCik') is not None else 'N/A'
    issuer_ticker = issuer.find('issuerTradingSymbol').text if issuer is not None and issuer.find('issuerTradingSymbol') is not None else 'N/A'
    
    # Extract reporting owner info
    reporting_owner = root.find('.//reportingOwner')
    owner_name = 'N/A'
    owner_relationship = {}
    
    if reporting_owner is not None:
        owner_id = reporting_owner.find('.//rptOwnerName')
        if owner_id is not None:
            owner_name = owner_id.find('rptOwnerName').text if owner_id.find('rptOwnerName') is not None else 'N/A'
        
        # Get relationship
        relationship = reporting_owner.find('.//reportingOwnerRelationship')
        if relationship is not None:
            owner_relationship = {
                'isDirector': relationship.find('isDirector').text if relationship.find('isDirector') is not None else 'false',
                'isOfficer': relationship.find('isOfficer').text if relationship.find('isOfficer') is not None else 'false',
                'isTenPercentOwner': relationship.find('isTenPercentOwner').text if relationship.find('isTenPercentOwner') is not None else 'false',
                'isOther': relationship.find('isOther').text if relationship.find('isOther') is not None else 'false',
                'officerTitle': relationship.find('officerTitle').text if relationship.find('officerTitle') is not None else None,
            }
    
    # Extract non-derivative transactions
    transactions = []
    for txn in root.findall('.//nonDerivativeTransaction'):
        security_title = txn.find('.//securityTitle/value')
        transaction_date = txn.find('.//transactionDate/value')
        transaction_code = txn.find('.//transactionCoding/transactionCode')
        transaction_shares = txn.find('.//transactionAmounts/transactionShares/value')
        transaction_price = txn.find('.//transactionAmounts/transactionPricePerShare/value')
        shares_owned_after = txn.find('.//postTransactionAmounts/sharesOwnedFollowingTransaction/value')
        ownership_nature = txn.find('.//ownershipNature/directOrIndirectOwnership/value')
        
        transactions.append({
            'security_title': security_title.text if security_title is not None else 'N/A',
            'transaction_date': transaction_date.text if transaction_date is not None else 'N/A',
            'transaction_code': transaction_code.text if transaction_code is not None else 'N/A',
            'shares': transaction_shares.text if transaction_shares is not None else '0',
            'price_per_share': transaction_price.text if transaction_price is not None else '0',
            'shares_owned_after': shares_owned_after.text if shares_owned_after is not None else '0',
            'ownership_nature': ownership_nature.text if ownership_nature is not None else 'D',
        })
    
    # Extract derivative transactions (options, warrants, etc.)
    derivative_transactions = []
    for txn in root.findall('.//derivativeTransaction'):
        security_title = txn.find('.//securityTitle/value')
        transaction_date = txn.find('.//transactionDate/value')
        transaction_code = txn.find('.//transactionCoding/transactionCode')
        exercise_price = txn.find('.//conversionOrExercisePrice/value')
        transaction_shares = txn.find('.//transactionAmounts/transactionShares/value')
        
        derivative_transactions.append({
            'security_title': security_title.text if security_title is not None else 'N/A',
            'transaction_date': transaction_date.text if transaction_date is not None else 'N/A',
            'transaction_code': transaction_code.text if transaction_code is not None else 'N/A',
            'shares': transaction_shares.text if transaction_shares is not None else '0',
            'exercise_price': exercise_price.text if exercise_price is not None else '0',
        })
    
    # Get footnotes (often contain important context)
    footnotes = []
    for footnote in root.findall('.//footnote'):
        footnote_id = footnote.get('id', 'N/A')
        footnote_text = footnote.text if footnote.text else 'N/A'
        footnotes.append({
            'id': footnote_id,
            'text': footnote_text
        })
    
    return {
        'issuer': {
            'name': issuer_name,
            'cik': issuer_cik,
            'ticker': issuer_ticker,
        },
        'reporting_owner': {
            'name': owner_name,
            'relationship': owner_relationship,
        },
        'non_derivative_transactions': transactions,
        'derivative_transactions': derivative_transactions,
        'footnotes': footnotes,
    }


if __name__ == '__main__':
    # Get latest Form 4 for ADC
    print('='*100)
    print('Analyzing latest Form 4 for ADC from EDGAR')
    print('='*100)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }
    
    # Get list of Form 4s
    cik = '917251'
    url = f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&count=5'
    
    response = requests.get(url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    table = soup.find('table', {'class': 'tableFile2'})
    if not table:
        print('No filings found')
        exit(1)
    
    rows = table.find_all('tr')[1:]
    if not rows:
        print('No Form 4 rows found')
        exit(1)
    
    # Get the first (latest) Form 4
    first_row = rows[0]
    cols = first_row.find_all('td')
    
    filing_date = cols[3].text.strip()
    doc_link = cols[1].find('a', {'id': 'documentsbutton'})
    
    if not doc_link:
        print('No document link found')
        exit(1)
    
    filing_index_url = 'https://www.sec.gov' + doc_link['href']
    
    print(f'\nLatest filing date: {filing_date}')
    print(f'Filing index URL: {filing_index_url}')
    
    # Get XML URL
    xml_url = get_form4_xml_url(filing_index_url)
    if not xml_url:
        print('Could not find XML file')
        exit(1)
    
    print(f'XML URL: {xml_url}\n')
    
    # Parse Form 4
    form4_data = parse_form4_xml(xml_url)
    
    print('\n' + '='*100)
    print('FORM 4 DATA EXTRACTED')
    print('='*100)
    print(json.dumps(form4_data, indent=2))
    
    print('\n\n' + '='*100)
    print('ANALYSIS: What EDGAR provides vs OpenInsider')
    print('='*100)
    
    print('\n✓ EDGAR PROVIDES:')
    print('  - Exact ownership percentages')
    print('  - Post-transaction ownership amounts')
    print('  - Direct vs indirect ownership designation')
    print('  - Derivative securities (options, warrants, etc.)')
    print('  - Exercise prices for options')
    print('  - Detailed footnotes with context')
    print('  - Structured relationship data (isDirector, isOfficer, isTenPercentOwner)')
    print('  - Complete historical data (not limited to 2 years)')
    print('  - Transaction codes (P=Purchase, S=Sale, A=Award, M=Exercise, etc.)')
    
    print('\n✗ OPENINSIDER PROVIDES (but EDGAR also has):')
    print('  - Trade date')
    print('  - Shares traded')
    print('  - Price per share')
    print('  - Total transaction value')
    print('  - Insider name and title')
    
    print('\n⚠️  KEY ADVANTAGES OF EDGAR:')
    print('  1. COMPLETE HISTORY - Goes back years, not limited to ~2 years')
    print('  2. DERIVATIVE TRANSACTIONS - Options grants, exercises (huge for insider sentiment)')
    print('  3. OWNERSHIP CONTEXT - See exact post-transaction ownership %')
    print('  4. FOOTNOTES - Often explain WHY trades happened (10b5-1 plans, estate planning, etc.)')
    print('  5. STRUCTURED DATA - Easier to filter by officer type programmatically')
