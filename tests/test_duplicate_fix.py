#!/usr/bin/env python3
"""Test script to verify the duplicate fix in trade_tracker.py"""
import os
import sys

# Add project root to path
sys.path.insert(0, '/app')

def test_duplicate_fix():
    print('Test 1: Importing TradeTracker...')
    from src.core.trade_tracker import TradeTracker
    print('✅ TradeTracker imported successfully')

    print('\nTest 2: Testing _is_duplicate_in_history method...')
    tracker = TradeTracker()

    # Check if method exists
    if hasattr(tracker, '_is_duplicate_in_history'):
        print('✅ Method _is_duplicate_in_history exists')

        # Test with existing dealId from trade_history.json
        result = tracker._is_duplicate_in_history('2035412681785081857')
        print(f'  - Check for existing dealId (2035412681785081857): {result}')
        assert result == True, "Should return True for existing dealId"

        # Test with non-existing dealId
        result2 = tracker._is_duplicate_in_history('NONEXISTENT123')
        print(f'  - Check for non-existing dealId (NONEXISTENT123): {result2}')
        assert result2 == False, "Should return False for non-existing dealId"

        # Test with None/empty dealId
        result3 = tracker._is_duplicate_in_history('')
        print(f'  - Check for empty dealId: {result3}')
        assert result3 == False, "Should return False for empty dealId"

        result4 = tracker._is_duplicate_in_history(None)
        print(f'  - Check for None dealId: {result4}')
        assert result4 == False, "Should return False for None dealId"
    else:
        print('❌ Method _is_duplicate_in_history NOT found')
        return False

    print('\n✅ All tests passed!')
    return True

if __name__ == '__main__':
    test_duplicate_fix()
