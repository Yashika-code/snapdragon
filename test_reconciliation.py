# SettleIQ Reconciliation Engine — Unit Tests

import unittest
from datetime import datetime, timedelta

def convert_to_paise(amount_float):
    """Convert float amount to integer paise."""
    return int(round(amount_float * 100))

def is_tier1_match(rp_utr, bank_utr, rp_amount, bank_amount, paise_tolerance=5):
    """
    Tier 1 Exact UTR Match check.
    Returns status and confidence.
    """
    if rp_utr and bank_utr and rp_utr == bank_utr:
        rp_paise = convert_to_paise(rp_amount)
        bank_paise = convert_to_paise(bank_amount)
        if abs(rp_paise - bank_paise) <= paise_tolerance:
            return "MATCHED", 1.0
    return "UNMATCHED", 0.0

def is_tier2_fuzzy_match(rp_amount, bank_amount, rp_date, bank_date, tolerance_pct=0.025, max_days_diff=3):
    """
    Tier 2 Fuzzy Match check based on amount tolerance (default 2.5%) and date difference.
    """
    if rp_amount <= 0:
        return False
    amt_diff_pct = abs(rp_amount - bank_amount) / rp_amount
    if amt_diff_pct > tolerance_pct:
        return False
    
    date_diff = (bank_date - rp_date).days
    if date_diff < 0 or date_diff > max_days_diff:
        return False
        
    return True

def classify_exception(rp_record, bank_records):
    """
    Classify exceptions for unmatched records or duplicate bank entries.
    """
    utr_counts = {}
    for b in bank_records:
        u = b.get('utr')
        if u:
            utr_counts[u] = utr_counts.get(u, 0) + 1
            
    if rp_record.get('utr') in utr_counts and utr_counts[rp_record.get('utr')] > 1:
        return 'Ghost Entry / Duplicate'
        
    # Check duplicate UTR in bank list directly if checking a bank record
    if rp_record.get('is_bank_record') and utr_counts.get(rp_record.get('utr'), 0) > 1:
        return 'Ghost Entry / Duplicate'

    matching_bank = [b for b in bank_records if b.get('utr') == rp_record.get('utr')]
    if not matching_bank:
        return 'Missing Entry (Bank)'
        
    return 'Other Exception'

class TestReconciliationEngine(unittest.TestCase):

    def test_1_paise_conversion_eliminates_floating_point_mismatch(self):
        """
        Test 1 — Paise conversion eliminates floating point mismatch.
        Shows that ₹5420.00 and ₹5419.99 would fail direct float comparison with strict equality,
        but pass when converted to integer paise with 5 paise tolerance.
        """
        rp_amount = 5420.00
        bank_amount = 5419.99
        
        # Direct float equality comparison fails
        self.assertNotEqual(rp_amount, bank_amount)
        
        # Integer paise conversion with 5 paise tolerance passes
        rp_paise = convert_to_paise(rp_amount)
        bank_paise = convert_to_paise(bank_amount)
        paise_diff = abs(rp_paise - bank_paise)
        
        self.assertEqual(rp_paise, 542000)
        self.assertEqual(bank_paise, 541999)
        self.assertLessEqual(paise_diff, 5)

    def test_2_tier1_exact_utr_match(self):
        """
        Test 2 — Tier 1 exact UTR match.
        Two records with identical UTR and amounts within 5 paise should return MATCHED status with 100% confidence.
        """
        rp_utr = "UTR123456789"
        bank_utr = "UTR123456789"
        rp_amount = 1000.00
        bank_amount = 1000.04  # 4 paise difference (within 5 paise tolerance)
        
        status, confidence = is_tier1_match(rp_utr, bank_utr, rp_amount, bank_amount)
        
        self.assertEqual(status, "MATCHED")
        self.assertEqual(confidence, 1.0)

    def test_3_tier2_fuzzy_match_accepts_within_tolerance(self):
        """
        Test 3 — Tier 2 fuzzy match accepts amount within 2.5% tolerance.
        A Razorpay record of ₹10,000 and bank record of ₹9,800 (2% difference) with date gap of 2 days should be accepted.
        """
        rp_amount = 10000.0
        bank_amount = 9800.0
        rp_date = datetime(2026, 3, 1)
        bank_date = datetime(2026, 3, 3)  # 2 days difference
        
        matched = is_tier2_fuzzy_match(rp_amount, bank_amount, rp_date, bank_date)
        
        self.assertTrue(matched)

    def test_4_tier2_rejects_amount_beyond_tolerance(self):
        """
        Test 4 — Tier 2 rejects amount beyond 2.5% tolerance.
        A Razorpay record of ₹10,000 and bank record of ₹9,500 (5% difference) should NOT match in Tier 2.
        """
        rp_amount = 10000.0
        bank_amount = 9500.0
        rp_date = datetime(2026, 3, 1)
        bank_date = datetime(2026, 3, 2)
        
        matched = is_tier2_fuzzy_match(rp_amount, bank_amount, rp_date, bank_date)
        
        self.assertFalse(matched)

    def test_5_missing_bank_entry_classified_correctly(self):
        """
        Test 5 — Missing bank entry classified correctly.
        A Razorpay record with no matching bank record should be classified as 'Missing Entry (Bank)' exception category.
        """
        rp_record = {'utr': 'UTR_RP_ONLY_999', 'amount': 5000.0}
        bank_records = [
            {'utr': 'UTR_BANK_1', 'amount': 5000.0},
            {'utr': 'UTR_BANK_2', 'amount': 2500.0}
        ]
        
        exception_cat = classify_exception(rp_record, bank_records)
        
        self.assertEqual(exception_cat, 'Missing Entry (Bank)')

    def test_6_duplicate_utr_detection(self):
        """
        Test 6 — Duplicate UTR detection.
        If the same UTR appears twice in bank statement, it should be flagged as 'Ghost Entry / Duplicate' exception category.
        """
        bank_records = [
            {'utr': 'DUP_UTR_777', 'amount': 1500.0},
            {'utr': 'DUP_UTR_777', 'amount': 1500.0}
        ]
        target_record = {'utr': 'DUP_UTR_777', 'is_bank_record': True}
        
        exception_cat = classify_exception(target_record, bank_records)
        
        self.assertEqual(exception_cat, 'Ghost Entry / Duplicate')

if __name__ == '__main__':
    unittest.main()
