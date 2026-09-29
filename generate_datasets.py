import pandas as pd
import numpy as np
# pyrefly: ignore [missing-import]
from faker import Faker
import random
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

fake = Faker('en_IN')
# Dynamic seed so each run generates fresh random settlements & anomaly ratios
dynamic_seed = int(datetime.now().timestamp() * 1000) % 100000
np.random.seed(dynamic_seed)
random.seed(dynamic_seed)

def generate_razorpay_data():
    """Fetch real data from Razorpay API or populate sandbox test items."""
    key_id = os.getenv("RAZORPAY_KEY_ID", "")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    
    data = []
    if key_id and key_secret:
        try:
            import razorpay
            client = razorpay.Client(auth=(key_id, key_secret))
            
            # Fetch existing settlements or payments
            settlements = client.settlement.all().get('items', [])
            payments = client.payment.all().get('items', [])
            
            if settlements:
                print(f"[+] Found {len(settlements)} real settlements from Razorpay API")
                for item in settlements:
                    data.append({
                        'payment_id': item.get('payment_id', f"pay_{fake.uuid4()[:8]}"),
                        'amount': round(item.get('amount', 0) / 100, 2),
                        'utr': item.get('utr', f"UTR{fake.random_number(digits=12)}"),
                        'date': pd.to_datetime(item.get('created_at', 0), unit='s').strftime('%Y-%m-%d'),
                        'merchant_id': item.get('entity', 'MERCH_RAZORPAY_LIVE'),
                        'status': item.get('status', 'settled'),
                        'mdr': round(item.get('fee', 0) / 100, 2),
                        'gst_on_mdr': round(item.get('tax', 0) / 100, 2)
                    })
            elif payments:
                print(f"[+] Found {len(payments)} real payment records from Razorpay API")
                for item in payments:
                    amt = round(item.get('amount', 0) / 100, 2)
                    fee = round(item.get('fee', amt * 0.02) / 100, 2) if item.get('fee') else round(amt * 0.02, 2)
                    tax = round(item.get('tax', fee * 0.18) / 100, 2) if item.get('tax') else round(fee * 0.18, 2)
                    data.append({
                        'payment_id': item.get('id', f"pay_{fake.uuid4()[:8]}"),
                        'amount': amt,
                        'utr': f"UTR{fake.random_number(digits=12)}",
                        'date': pd.to_datetime(item.get('created_at', datetime.now().timestamp()), unit='s').strftime('%Y-%m-%d'),
                        'merchant_id': 'MERCH_RAZORPAY_LIVE',
                        'status': item.get('status', 'captured'),
                        'mdr': fee,
                        'gst_on_mdr': tax
                    })
            else:
                print("[*] Sandbox API connected successfully (Account active, 0 past settlements found). Generating production-grade Razorpay Sandbox dataset.")
        except Exception as e:
            print(f"[*] Razorpay API notice: {e}. Generating production-grade Razorpay Sandbox dataset.")

    if not data:
        n_records = 500
        merchants = [f"MERCH_{i:03d}" for i in range(1, 6)]
        base_date = datetime.now() - timedelta(days=30)
        
        for i in range(1, 501):
            payment_id = f"pay_{fake.hexify(text='^^^^^^^^^^^^')}"
            amount = round(random.uniform(800, 45000), 2)
            utr = f"UTR{fake.random_number(digits=12)}" if random.random() > 0.10 else ""
            txn_date = base_date + timedelta(days=random.randint(0, 25))
            merchant_id = random.choice(merchants)
            status = random.choice(['settled', 'settled', 'settled', 'settled', 'pending'])
            mdr = round(amount * random.uniform(0.018, 0.025), 2)
            gst_on_mdr = round(mdr * 0.18, 2)
            
            data.append({
                'payment_id': payment_id,
                'amount': amount,
                'utr': utr,
                'date': txn_date.strftime('%Y-%m-%d'),
                'merchant_id': merchant_id,
                'status': status,
                'mdr': mdr,
                'gst_on_mdr': gst_on_mdr
            })
            
    df = pd.DataFrame(data)
    df.to_csv('razorpay_settlements.csv', index=False)
    print(f"[+] Generated {len(df)} Razorpay settlement records -> razorpay_settlements.csv")
    return df

def generate_bank_statement(razorpay_df):
    """Generate bank statements with realistic reconciliation anomalies."""
    data = []
    anomaly_log = []
    
    for idx, row in razorpay_df.iterrows():
        rnd = random.random()
        
        if rnd < 0.05:
            # Anomaly 1: Missing Entry in Bank (Settled in Razorpay, omitted from bank)
            anomaly_log.append({'type': 'Missing Entry (Bank)', 'payment_id': row['payment_id']})
            continue
            
        elif rnd < 0.09:
            # Anomaly 2: Amount Mismatch (Bank credit differs by ±2-5%)
            variation = random.choice([0.96, 0.97, 1.03, 1.04])
            bank_amount = round(row['amount'] * variation, 2)
            bank_date = pd.to_datetime(row['date']) + timedelta(days=1)
            anomaly_log.append({'type': 'Amount Mismatch', 'payment_id': row['payment_id'], 'rp_amt': row['amount'], 'bank_amt': bank_amount})
            
            data.append({
                'txn_ref': f"TXN{fake.random_number(digits=10)}",
                'utr': row['utr'],
                'amount': bank_amount,
                'value_date': bank_date.strftime('%Y-%m-%d'),
                'narration': f"NEFT-RAZORPAY-{row['merchant_id']}",
                'merchant_id': row['merchant_id']
            })
            
        elif rnd < 0.13:
            # Anomaly 3: Timing Mismatch (Settlement delayed by T+4 to T+7 days)
            bank_date = pd.to_datetime(row['date']) + timedelta(days=random.randint(4, 7))
            anomaly_log.append({'type': 'Timing Mismatch', 'payment_id': row['payment_id'], 'rp_date': row['date'], 'bank_date': bank_date.strftime('%Y-%m-%d')})
            
            data.append({
                'txn_ref': f"TXN{fake.random_number(digits=10)}",
                'utr': row['utr'],
                'amount': row['amount'],
                'value_date': bank_date.strftime('%Y-%m-%d'),
                'narration': f"NEFT-RAZORPAY-{row['merchant_id']}",
                'merchant_id': row['merchant_id']
            })
            
        elif rnd < 0.16:
            # Anomaly 4: Duplicate Entry in Bank (Duplicate UTR credit)
            bank_date = pd.to_datetime(row['date']) + timedelta(days=1)
            data.append({
                'txn_ref': f"TXN{fake.random_number(digits=10)}",
                'utr': row['utr'],
                'amount': row['amount'],
                'value_date': bank_date.strftime('%Y-%m-%d'),
                'narration': f"NEFT-RAZORPAY-{row['merchant_id']}",
                'merchant_id': row['merchant_id']
            })
            data.append({
                'txn_ref': f"TXN{fake.random_number(digits=10)}",
                'utr': row['utr'],
                'amount': row['amount'],
                'value_date': bank_date.strftime('%Y-%m-%d'),
                'narration': f"NEFT-RAZORPAY-DUP-{row['merchant_id']}",
                'merchant_id': row['merchant_id']
            })
            anomaly_log.append({'type': 'Ghost Entry / Duplicate', 'payment_id': row['payment_id']})
            
        else:
            # Normal T+1 or T+2 settlement match
            bank_date = pd.to_datetime(row['date']) + timedelta(days=random.choice([1, 2]))
            data.append({
                'txn_ref': f"TXN{fake.random_number(digits=10)}",
                'utr': row['utr'],
                'amount': row['amount'],
                'value_date': bank_date.strftime('%Y-%m-%d'),
                'narration': f"NEFT-RAZORPAY-{row['merchant_id']}",
                'merchant_id': row['merchant_id']
            })
            
    # Anomaly 5: Missing Entry in Razorpay (Bank credit with no Razorpay record)
    for i in range(3):
        extra_date = datetime.now() - timedelta(days=random.randint(5, 20))
        extra_amt = round(random.uniform(2000, 15000), 2)
        data.append({
            'txn_ref': f"TXN{fake.random_number(digits=10)}",
            'utr': f"UTR{fake.random_number(digits=12)}",
            'amount': extra_amt,
            'value_date': extra_date.strftime('%Y-%m-%d'),
            'narration': "DIRECT-UPI-CREDIT-UNLINKED",
            'merchant_id': random.choice([f"MERCH_{j:03d}" for j in range(1, 6)])
        })
        anomaly_log.append({'type': 'Missing Entry (Razorpay)', 'amount': extra_amt})

    df = pd.DataFrame(data)
    df.to_csv('bank_statement.csv', index=False)
    print(f"[+] Generated {len(df)} bank statement records with injected anomalies -> bank_statement.csv")
    return df, anomaly_log

def generate_gst_records(razorpay_df):
    """Generate GST Invoices dataset linked to Razorpay settlements."""
    data = []
    for idx, row in razorpay_df.iterrows():
        if random.random() > 0.25:
            taxable = round(row['amount'] / 1.18, 2)
            gst = round(row['amount'] - taxable, 2)
            
            if random.random() < 0.05:
                gst = round(gst * random.choice([0.85, 1.15]), 2)
            
            data.append({
                'invoice_no': f"INV-2026-{fake.random_number(digits=6)}",
                'taxable_amount': taxable,
                'gst_amount': gst,
                'total_amount': round(taxable + gst, 2),
                'date': row['date'],
                'merchant_id': row['merchant_id'],
                'payment_id': row['payment_id']
            })
            
    df = pd.DataFrame(data)
    df.to_csv('gst_records.csv', index=False)
    print(f"[+] Generated {len(df)} GST records -> gst_records.csv")
    return df

def main():
    print("=== Initializing SettleIQ Dataset Generation Pipeline ===")
    rp_df = generate_razorpay_data()
    bank_df, anomalies = generate_bank_statement(rp_df)
    gst_df = generate_gst_records(rp_df)
    
    print("\n--- Generation Summary ---")
    print(f"Razorpay Settlements: {len(rp_df)} records")
    print(f"Bank Transactions: {len(bank_df)} records")
    print(f"GST Invoices: {len(gst_df)} records")
    print(f"Total Anomalies Injected: {len(anomalies)}")

if __name__ == "__main__":
    main()
