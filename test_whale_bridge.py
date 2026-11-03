import unittest
from unittest.mock import patch
import whale_bridge


class WhaleBridgeTests(unittest.TestCase):
    def test_unavailable_is_explicit(self):
        with patch.object(whale_bridge, '_get', side_effect=ConnectionError):
            result = whale_bridge.whale_data()
        self.assertFalse(result['available'])
        self.assertEqual(result['rows'], [])
        self.assertFalse(result['broker_orders_enabled'])

    def test_preserves_feed_provenance(self):
        with patch.object(whale_bridge, '_get', side_effect=[
            {'feed': 'synthetic'}, {'events': [{'id': 'unit-test'}]}
        ]):
            result = whale_bridge.whale_data()
        self.assertTrue(result['available'])
        self.assertEqual(result['status']['feed'], 'synthetic')
        self.assertEqual(result['rows'][0]['id'], 'unit-test')

    def test_invalid_upstream_shape(self):
        with patch.object(whale_bridge, '_get', side_effect=[{}, {'events': None}]):
            self.assertFalse(whale_bridge.whale_data()['available'])


if __name__ == '__main__':
    unittest.main()
