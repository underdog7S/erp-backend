"""Retail procurement actions: receive a purchase order into stock, and move a stock transfer
through dispatch -> complete. Each is all-or-nothing and locks the rows it changes."""
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models.permissions import HasFeaturePermissionFactory
from api.retail_stock import credit_stock, debit_stock
from retail.models import (
    GoodsReceipt, GoodsReceiptItem, PurchaseOrder, StockTransfer, Warehouse,
)


def _tenant(request):
    return request.user.userprofile.tenant


class RetailPurchaseOrderReceiveView(APIView):
    """POST {"warehouse": id, "items": [{"item": <po item id>, "quantity": n}, ...]}

    Partial deliveries are allowed: each call books a goods receipt, adds the stock to the
    warehouse and moves the order to PARTIAL_RECEIVED or RECEIVED.
    """
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]

    def post(self, request, pk):
        tenant = _tenant(request)
        with transaction.atomic():
            po = PurchaseOrder.objects.select_for_update().filter(pk=pk, tenant=tenant).first()
            if not po:
                return Response({'error': 'Purchase order not found.'}, status=status.HTTP_404_NOT_FOUND)
            if po.status in ('RECEIVED', 'CANCELLED'):
                return Response({'error': f'This order is already {po.status.lower()}.'}, status=status.HTTP_400_BAD_REQUEST)
            warehouse = Warehouse.objects.filter(pk=request.data.get('warehouse'), tenant=tenant).first()
            if not warehouse:
                raise ValidationError({'warehouse': 'Choose the warehouse the goods arrived at.'})
            lines = {i.id: i for i in po.items.select_related('product')}
            rows = [r for r in (request.data.get('items') or []) if int(r.get('quantity') or 0) > 0]
            if not rows:
                raise ValidationError({'items': 'Enter a received quantity for at least one line.'})

            receipt = GoodsReceipt.objects.create(
                tenant=tenant, purchase_order=po, receipt_date=timezone.now().date(),
                warehouse=warehouse, received_by=request.user.userprofile)
            for r in rows:
                line = lines.get(r.get('item'))
                if not line:
                    raise ValidationError({'items': 'A line does not belong to this order.'})
                qty = int(r['quantity'])
                outstanding = line.quantity - line.received_quantity
                if qty > outstanding:
                    raise ValidationError({'items': f'{line.product.name}: only {outstanding} still to receive.'})
                GoodsReceiptItem.objects.create(
                    tenant=tenant, goods_receipt=receipt, purchase_order_item=line,
                    quantity_received=qty, quality_check='PASSED')
                line.received_quantity += qty
                line.save(update_fields=['received_quantity'])
                credit_stock(tenant, line.product, warehouse, qty)

            done = all(i.received_quantity >= i.quantity for i in lines.values())
            po.status = 'RECEIVED' if done else 'PARTIAL_RECEIVED'
            po.save(update_fields=['status'])
        return Response({'message': 'Stock received.', 'receipt': receipt.gr_number, 'status': po.status},
                        status=status.HTTP_201_CREATED)


class _TransferAction(APIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    from_status = ()
    to_status = ''

    def apply(self, tenant, transfer):
        raise NotImplementedError

    def post(self, request, pk):
        tenant = _tenant(request)
        with transaction.atomic():
            transfer = StockTransfer.objects.select_for_update().filter(pk=pk, tenant=tenant).first()
            if not transfer:
                return Response({'error': 'Transfer not found.'}, status=status.HTTP_404_NOT_FOUND)
            if transfer.status not in self.from_status:
                return Response({'error': f'A {transfer.status.lower().replace("_", " ")} transfer cannot do this.'},
                                status=status.HTTP_400_BAD_REQUEST)
            self.apply(tenant, transfer)
            transfer.status = self.to_status
            transfer.save(update_fields=['status'])
        return Response({'message': 'Updated.', 'status': transfer.status})


class RetailTransferDispatchView(_TransferAction):
    """Take the stock out of the sending warehouse; it is now in transit."""
    from_status = ('DRAFT',)
    to_status = 'IN_TRANSIT'

    def apply(self, tenant, transfer):
        for item in transfer.items.select_related('product'):
            debit_stock(tenant, item.product, transfer.from_warehouse, item.quantity)


class RetailTransferCompleteView(_TransferAction):
    """Book the stock into the receiving warehouse."""
    from_status = ('IN_TRANSIT',)
    to_status = 'COMPLETED'

    def apply(self, tenant, transfer):
        for item in transfer.items.select_related('product'):
            credit_stock(tenant, item.product, transfer.to_warehouse, item.quantity)


class RetailTransferCancelView(_TransferAction):
    """Cancel a transfer that has not left yet."""
    from_status = ('DRAFT',)
    to_status = 'CANCELLED'

    def apply(self, tenant, transfer):
        pass
