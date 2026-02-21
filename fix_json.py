#!/usr/bin/env python3
import json

# Read the corrupted file
with open('output CSVs/insider_conviction_all_stocks_results.json', 'r') as f:
    content = f.read()

# Find where 'events' starts in the last result
last_events_pos = content.rfind('"events"')
if last_events_pos > 0:
    # Find the closing of trades array before events
    trades_end = content.rfind(']', 0, last_events_pos)
    # Close the result object properly
    content_fixed = content[:trades_end+1] + '\n    }\n  ]\n}'
    
    # Try to parse it
    try:
        data = json.loads(content_fixed)
        print(f'✅ Successfully fixed! {len(data.get("all_results", []))} results')
        
        # Save it
        with open('output CSVs/insider_conviction_all_stocks_results.json', 'w') as f:
            json.dump(data, f, indent=2)
        print('💾 Saved fixed version')
    except Exception as e:
        print(f'❌ Fix failed: {e}')
