#!/usr/bin/env python3
"""Test script to verify the sync enrichment fix"""
import sys
sys.path.insert(0, '/app')

# Test that the code imports correctly
print('Test: Import telegram panel trades...')
from src.telegram_panel.backend.routes import trades
print('✅ Imports successful')

# Verify the sync function has the enrichment code
import inspect
source = inspect.getsource(trades.sync_positions)
if 'get_recent_orders' in source:
    print('✅ get_recent_orders found in sync_positions')
else:
    print('❌ get_recent_orders NOT found in sync_positions')

if 'OrderStatus' in source:
    print('✅ OrderStatus handling found')
else:
    print('❌ OrderStatus handling NOT found')
