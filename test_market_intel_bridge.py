import unittest
import os
import sys
import json
from unittest.mock import patch

# Add the current directory to the path so we can import market_intel_bridge
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import market_intel_bridge

class TestMarketIntelBridge(unittest.TestCase):
    
    def setUp(self):
        # Clear the cache before each test
        market_intel_bridge._load_data.cache_clear()
        # Create a temporary fixture directory
        self.fixture_dir = os.path.join(os.path.dirname(__file__), 'test_fixtures')
        os.makedirs(self.fixture_dir, exist_ok=True)
        
        # Create a small synthetic fixture for congress
        self.congress_fixture = [
            {
                "id": "test:0",
                "chamber": "senate",
                "member": {"name": "Test Member", "bioguideId": "T000000", "party": "Independent", "state": "XX"},
                "filedAt": "2026-01-01",
                "transactedAt": "2026-01-01",
                "ticker": "TEST",
                "assetDescription": "Test Asset",
                "assetType": "stock",
                "side": "buy",
                "amountRange": {"min": 1000, "max": 5000, "text": "$1,000 - $5,000"},
                "owner": "self",
                "provenance": {
                    "source": "test-source",
                    "sourceUrl": "https://example.com/test",
                    "retrievedAt": "2026-01-01T00:00:00Z",
                    "parser": "test-parser@1",
                    "confidence": 1.0,
                    "needsReview": False
                }
            },
            {
                "id": "test:1",
                "chamber": "house",
                "member": {"name": "Test Member 2", "bioguideId": "T000001", "party": "Independent", "state": "XX"},
                "filedAt": "2026-01-02",
                "transactedAt": "2026-01-02",
                "ticker": "TEST2",
                "assetDescription": "Test Asset 2",
                "assetType": "stock",
                "side": "sell",
                "amountRange": {"min": 5000, "max": 10000, "text": "$5,000 - $10,000"},
                "owner": "spouse",
                "provenance": {
                    "source": "test-source",
                    "sourceUrl": "https://example.com/test2",
                    "retrievedAt": "2026-01-02T00:00:00Z",
                    "parser": "test-parser@1",
                    "confidence": 1.0,
                    "needsReview": False
                }
            }
        ]
        
        # Write the fixture file for congress
        congress_dir = os.path.join(self.fixture_dir, 'congress', 'trades')
        os.makedirs(congress_dir, exist_ok=True)
        with open(os.path.join(congress_dir, 'latest.json'), 'w') as f:
            json.dump(self.congress_fixture, f)
    
    def tearDown(self):
        # Remove the fixture directory
        import shutil
        if os.path.exists(self.fixture_dir):
            shutil.rmtree(self.fixture_dir)
        # Clear cache after test to avoid interference
        market_intel_bridge._load_data.cache_clear()
    
    def test_unknown_kind(self):
        result = market_intel_bridge.get_market_intel('unknown_kind')
        self.assertFalse(result['available'])
        self.assertEqual(result['rows'], [])
        self.assertIn('Unknown kind: unknown_kind', result['reason'])
    
    def test_missing_data(self):
        # We'll test with a kind that is known but we point to a non-existent fixture by temporarily changing the base path
        # We'll use patch to change the BASE_DATA_PATH in the module to a non-existent directory
        with patch('market_intel_bridge.BASE_DATA_PATH', '/non/existent/path'):
            result = market_intel_bridge.get_market_intel('congress')
            self.assertFalse(result['available'])
            self.assertEqual(result['rows'], [])
            self.assertIn('Data not found for kind: congress', result['reason'])
    
    def test_fixture_loads_and_preserves_provenance(self):
        # Patch the BASE_DATA_PATH to our fixture directory
        with patch('market_intel_bridge.BASE_DATA_PATH', self.fixture_dir):
            result = market_intel_bridge.get_market_intel('congress', limit=10)
            self.assertTrue(result['available'])
            self.assertEqual(len(result['rows']), 2)
            # Check that the first row has the expected provenance.sourceUrl
            self.assertEqual(result['rows'][0]['provenance']['sourceUrl'], 'https://example.com/test')
            self.assertEqual(result['rows'][1]['provenance']['sourceUrl'], 'https://example.com/test2')
            # Also check that other fields are present
            self.assertEqual(result['rows'][0]['ticker'], 'TEST')
            self.assertEqual(result['rows'][1]['ticker'], 'TEST2')
    
    def test_symbol_filtering(self):
        with patch('market_intel_bridge.BASE_DATA_PATH', self.fixture_dir):
            # Filter by symbol TEST
            result = market_intel_bridge.get_market_intel('congress', symbol='TEST', limit=10)
            self.assertTrue(result['available'])
            self.assertEqual(len(result['rows']), 1)
            self.assertEqual(result['rows'][0]['ticker'], 'TEST')
            # Filter by symbol TEST2
            result = market_intel_bridge.get_market_intel('congress', symbol='TEST2', limit=10)
            self.assertTrue(result['available'])
            self.assertEqual(len(result['rows']), 1)
            self.assertEqual(result['rows'][0]['ticker'], 'TEST2')
            # Filter by symbol that doesn't exist
            result = market_intel_bridge.get_market_intel('congress', symbol='NONEXISTENT', limit=10)
            self.assertTrue(result['available'])
            self.assertEqual(len(result['rows']), 0)
    
    def test_limit(self):
        with patch('market_intel_bridge.BASE_DATA_PATH', self.fixture_dir):
            # We have 2 rows in fixture, limit 1 should return 1 row
            result = market_intel_bridge.get_market_intel('congress', limit=1)
            self.assertTrue(result['available'])
            self.assertEqual(len(result['rows']), 1)
            # Limit 0 should return 0 rows
            result = market_intel_bridge.get_market_intel('congress', limit=0)
            self.assertTrue(result['available'])
            self.assertEqual(len(result['rows']), 0)
            # Limit larger than available should return all
            result = market_intel_bridge.get_market_intel('congress', limit=10)
            self.assertTrue(result['available'])
            self.assertEqual(len(result['rows']), 2)
    
    def test_cache_behaviour(self):
        # We'll test that the same kind loads from cache by checking that the file is only opened once.
        # We can mock the open function and count calls.
        with patch('market_intel_bridge.BASE_DATA_PATH', self.fixture_dir):
            with patch('builtins.open', side_effect=open) as mock_open:
                # Clear the cache first
                market_intel_bridge._load_data.cache_clear()
                # Call the function twice
                result1 = market_intel_bridge.get_market_intel('congress')
                result2 = market_intel_bridge.get_market_intel('congress')
                # The open should have been called only once due to caching
                self.assertEqual(mock_open.call_count, 1)
                # Both results should be available and have the same data
                self.assertTrue(result1['available'])
                self.assertTrue(result2['available'])
                self.assertEqual(len(result1['rows']), len(result2['rows']))
    
    def test_defensive_missing_file(self):
        # Test that if the file is missing, we return available=False and not an exception
        # We already tested missing_data, but let's also test with a kind that exists in config but file missing
        # We'll use a kind that we know exists but we remove the file temporarily? Instead, we can point to a directory without the file.
        # We'll create a temporary directory for a kind and not put the file there.
        kind = 'insider'
        # Create a directory structure for insider but without the file
        insider_dir = os.path.join(self.fixture_dir, 'insider', 'transactions')
        os.makedirs(insider_dir, exist_ok=True)
        # Do not create latest.json
        with patch('market_intel_bridge.BASE_DATA_PATH', self.fixture_dir):
            result = market_intel_bridge.get_market_intel(kind)
            self.assertFalse(result['available'])
            self.assertEqual(result['rows'], [])
            self.assertIn('Data not found for kind: insider', result['reason'])

if __name__ == '__main__':
    unittest.main()