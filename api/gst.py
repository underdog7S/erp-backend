"""Small GST helpers shared by the industry modules.

Prices in India are usually quoted GST-inclusive (a medicine's MRP always is), so the default
is to *extract* the tax that is already inside the price rather than add more on top.
"""
import re
from decimal import Decimal, ROUND_HALF_UP

TWO = Decimal('0.01')
GSTIN_RE = re.compile(r'^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]$')
_CHARS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'


def money(value):
    return Decimal(value).quantize(TWO, rounding=ROUND_HALF_UP)


def line_tax(amount, rate, inclusive=True):
    """Returns (taxable_value, tax) for one invoice line.

    inclusive: `amount` already contains the tax, so it is taken out of the amount.
    exclusive: tax is added on top of `amount`.
    """
    amount = Decimal(str(amount))
    rate = Decimal(str(rate or 0))
    if rate <= 0 or amount <= 0:
        return money(amount), Decimal('0.00')
    if inclusive:
        tax = money(amount * rate / (100 + rate))
        return money(amount - tax), tax
    tax = money(amount * rate / 100)
    return money(amount), tax


def split_cgst_sgst(tax):
    """Intra-state supply: half central, half state. The two always add back to `tax` exactly."""
    tax = money(tax)
    cgst = money(tax / 2)
    return cgst, tax - cgst


def state_code(gstin):
    gstin = (gstin or '').strip()
    return gstin[:2] if len(gstin) >= 2 and gstin[:2].isdigit() else ''


def is_intra_state(seller_gstin, buyer_gstin='', place_of_supply=''):
    """True when CGST+SGST applies, False when IGST applies. Unknown buyer state counts as intra-state,
    the normal case for a counter sale."""
    seller = state_code(seller_gstin)
    buyer = (place_of_supply or '').strip() or state_code(buyer_gstin)
    if not seller or not buyer:
        return True
    return seller == buyer


def is_valid_gstin(gstin):
    """Format and check-digit validation for a 15-character GSTIN."""
    gstin = (gstin or '').strip().upper()
    if not GSTIN_RE.match(gstin):
        return False
    total = 0
    for i, ch in enumerate(gstin[:14]):
        value = _CHARS.index(ch) * (1 if i % 2 == 0 else 2)
        total += value // 36 + value % 36
    return _CHARS[(36 - total % 36) % 36] == gstin[14]
