"""Stock movement helpers for the retail module (purchase receipts, transfers, adjustments).

Every movement goes through here so Inventory rows are locked while they change and
stock can never silently go negative.
"""
from django.db import transaction
from rest_framework.exceptions import ValidationError

from retail.models import Inventory


def _locked_row(tenant, product, warehouse):
    row, _ = Inventory.objects.select_for_update().get_or_create(
        tenant=tenant, product=product, warehouse=warehouse)
    return row


@transaction.atomic
def credit_stock(tenant, product, warehouse, qty):
    row = _locked_row(tenant, product, warehouse)
    row.quantity_on_hand += qty
    row.save()
    return row


@transaction.atomic
def debit_stock(tenant, product, warehouse, qty):
    row = _locked_row(tenant, product, warehouse)
    if row.quantity_available < qty:
        raise ValidationError({'items_input': f'{product.name}: only {row.quantity_available} available in {warehouse.name}.'})
    row.quantity_on_hand -= qty
    row.save()
    return row
