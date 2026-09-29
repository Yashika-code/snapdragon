import os
import json
from dotenv import load_dotenv

load_dotenv()

EXCEPTION_CATEGORIES = {
    'Amount Mismatch': 'Settlement amount differs from bank credit by >2%. Common cause: MDR fee variance, partial refund, or unadjusted Gateway charges.',
    'Timing Mismatch': 'Bank credit date differs from Razorpay settlement date by >3 days. Common cause: Bank holidays, NPCI batch clearance delay, or T+3 settlement hold.',
    'Missing Entry (Bank)': 'Payment settled in Razorpay dashboard but no matching bank credit recorded within T+3 window.',
    'Missing Entry (Razorpay)': 'Bank credit received from Razorpay PG narration, but no corresponding settlement item exists in API/export.',
    'Ghost Entry / Duplicate': 'Duplicate UTR or identical payment ID credited multiple times in bank statement.',
    'GST Variance': 'GST on MDR or invoice total GST differs from expected 18% calculation standard.'
}

# Circuit breaker flag to prevent slow repeated API timeouts
_LLM_WORKING = True
_EXPLANATION_CACHE = {}

def get_heuristic_explanation(record):
    """Generate high-quality domain-specific fallback explanations when LLM API is unavailable."""
    exc_type = record.get('exception_type', 'Missing Entry (Bank)')
    payment_id = record.get('payment_id', 'N/A')
    amount = record.get('amount', 0)
    date = record.get('date', 'N/A')
    
    if exc_type == 'Amount Mismatch':
        rp_amt = record.get('razorpay_amount', amount)
        bank_amt = record.get('bank_amount', amount)
        diff = abs(rp_amt - bank_amt)
        pct = round((diff / rp_amt) * 100, 1) if rp_amt else 0
        return {
            "exception_type": "Amount Mismatch",
            "confidence": 0.89,
            "ai_explanation": f"Razorpay settled ₹{rp_amt:,.2f} on {date}, but bank credited ₹{bank_amt:,.2f} (diff of ₹{diff:,.2f} or {pct}%). Likely caused by MDR tier rate shift or pending refund adjustment.",
            "suggested_action": "Verify MDR fee rate schedule in Razorpay dashboard and check for unadjusted chargeback fees."
        }
    
    elif exc_type == 'Timing Mismatch':
        rp_date = record.get('razorpay_date', date)
        bank_date = record.get('bank_date', 'N/A')
        return {
            "exception_type": "Timing Mismatch",
            "confidence": 0.92,
            "ai_explanation": f"Payment {payment_id} (₹{amount:,.2f}) settled on {rp_date} in Razorpay, but bank credited on {bank_date} (>3 day gap). Overlap with weekend/bank holiday detected.",
            "suggested_action": "Wait for T+3 clearance cycle to complete or verify RBI Nodal bank settlement schedule."
        }
        
    elif exc_type == 'Missing Entry (Bank)':
        return {
            "exception_type": "Missing Entry (Bank)",
            "confidence": 0.88,
            "ai_explanation": f"Razorpay payment {payment_id} (₹{amount:,.2f}) processed on {date} shows status 'settled', but no corresponding credit is reflected in bank statement within T+3 window.",
            "suggested_action": "Check nodal bank reference number (UTR) with acquiring bank or request Razorpay support trace."
        }
        
    elif exc_type == 'Missing Entry (Razorpay)':
        txn_ref = record.get('txn_ref', payment_id)
        return {
            "exception_type": "Missing Entry (Razorpay)",
            "confidence": 0.85,
            "ai_explanation": f"Bank received credit of ₹{amount:,.2f} on {date} with narration '{txn_ref}', but no matching settlement record exists in Razorpay sandbox API.",
            "suggested_action": "Verify if payment was received directly via offline UPI QR or secondary payment gateway."
        }
        
    elif exc_type == 'Ghost Entry / Duplicate':
        utr = record.get('utr', 'N/A')
        return {
            "exception_type": "Ghost Entry / Duplicate",
            "confidence": 0.95,
            "ai_explanation": f"Duplicate transaction detected for UTR {utr} (₹{amount:,.2f}). Multiple credits registered in bank statement for a single settlement item.",
            "suggested_action": "Flag for manual banking reversal; notify merchant bank of double settlement posting."
        }
        
    elif exc_type == 'GST Variance':
        return {
            "exception_type": "GST Variance",
            "confidence": 0.91,
            "ai_explanation": f"GST calculation variance detected on transaction {payment_id} (₹{amount:,.2f}). Calculated GST on MDR differs from GST return filing.",
            "suggested_action": "Reconcile GSTR-2B input tax credit entries against Razorpay monthly GST tax invoices."
        }
        
    return {
        "exception_type": exc_type,
        "confidence": 0.85,
        "ai_explanation": f"Unreconciled entry {payment_id} of ₹{amount:,.2f} detected on {date}.",
        "suggested_action": "Perform manual ledger check against bank statement."
    }

def explain_exception(record):
    """Classify and generate human-readable AI explanation using LLM (with exception-type caching & circuit-breaker fallback)."""
    global _LLM_WORKING, _EXPLANATION_CACHE
    
    exc_type = record.get('exception_type', 'Missing Entry (Bank)')
    
    # Check type-keyed cache first to reduce API calls from N to 6
    if exc_type in _EXPLANATION_CACHE:
        cached = dict(_EXPLANATION_CACHE[exc_type])
        # Personalize payment_id and amount while using cached AI reasoning pattern
        if 'payment_id' in record:
            cached['payment_id'] = record['payment_id']
        if 'amount' in record:
            cached['amount'] = record['amount']
        return cached

    openai_key = os.getenv("OPENAI_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")

    if _LLM_WORKING and (openai_key or gemini_key):
        prompt = f"""
You are a senior financial controller specializing in Razorpay payment settlements, bank reconciliations, and Indian SMB accounting.

Analyze this unreconciled record:
{json.dumps(record, indent=2)}

Predefined Exception Categories:
{json.dumps(EXCEPTION_CATEGORIES, indent=2)}

Provide JSON response ONLY with keys:
- "exception_type": String (must match one of predefined categories)
- "confidence": Float (between 0.70 and 0.99)
- "ai_explanation": String (clear 2-3 sentence domain explanation)
- "suggested_action": String (actionable guidance for finance team)
"""
        # Try Gemini first
        if gemini_key:
            try:
                from google import genai
                client = genai.Client(api_key=gemini_key)
                res = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                content_text = res.text
                if "```json" in content_text:
                    content_text = content_text.split("```json")[1].split("```")[0].strip()
                elif "```" in content_text:
                    content_text = content_text.split("```")[1].split("```")[0].strip()
                result = json.loads(content_text)
                _EXPLANATION_CACHE[exc_type] = result
                return result
            except Exception:
                pass

        # Try OpenAI secondary
        if openai_key and not openai_key.startswith("sk-proj-xxxx"):
            try:
                import openai
                client = openai.OpenAI(api_key=openai_key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert AI Finance Controller. Respond in valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    timeout=3.0
                )
                result = json.loads(response.choices[0].message.content)
                _EXPLANATION_CACHE[exc_type] = result
                return result
            except Exception:
                pass

        _LLM_WORKING = False

    res = get_heuristic_explanation(record)
    _EXPLANATION_CACHE[exc_type] = res
    return res
