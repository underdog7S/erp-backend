"""PDF downloads for order documents (purchase orders, sales orders, quotations)."""
import importlib

from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api import pdf_documents
from api.models.permissions import HasFeaturePermissionFactory


def _make(feature, model_path, builder, filename, related=()):
    class View(APIView):
        permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(feature)]

        def get(self, request, pk):
            module, name = model_path.rsplit('.', 1)
            model = getattr(importlib.import_module(module), name)
            qs = model.objects.filter(tenant=request.user.userprofile.tenant)
            if related:
                qs = qs.select_related(*related)
            obj = qs.filter(pk=pk).first()
            if not obj:
                return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
            response = HttpResponse(getattr(pdf_documents, builder)(obj), content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response

    View.__name__ = builder.title().replace('_', '') + 'PDFView'
    return View


ManufacturingSalesOrderPDFView = _make('manufacturing', 'manufacturing.models.SalesOrder', 'manufacturing_sales_order', 'sales-order.pdf', ('customer', 'warehouse'))
ManufacturingPurchaseOrderPDFView = _make('manufacturing', 'manufacturing.models.PurchaseOrder', 'manufacturing_purchase_order', 'purchase-order.pdf', ('supplier',))
RetailPurchaseOrderPDFView = _make('retail', 'retail.models.PurchaseOrder', 'retail_purchase_order', 'purchase-order.pdf', ('supplier',))
RetailQuotationPDFView = _make('retail', 'retail.models.Quotation', 'retail_quotation', 'quotation.pdf', ('customer',))
PharmacyPurchaseOrderPDFView = _make('pharmacy', 'pharmacy.models.PurchaseOrder', 'pharmacy_purchase_order', 'purchase-order.pdf', ('supplier',))
