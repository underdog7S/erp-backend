"""Business details a tenant admin maintains (currently the GST number used on invoices)."""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.gst import is_valid_gstin
from api.models.permissions import role_required


class BusinessDetailsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        t = request.user.userprofile.tenant
        return Response({'name': t.name, 'gstin': t.gstin, 'address': t.address, 'phone': t.phone})

    @role_required('admin', 'principal')
    def put(self, request):
        t = request.user.userprofile.tenant
        gstin = (request.data.get('gstin') or '').strip().upper()
        if gstin and not is_valid_gstin(gstin):
            return Response({'error': 'That GST number is not valid. It has 15 characters, for example 27AAPFU0939F1ZV.'}, status=status.HTTP_400_BAD_REQUEST)
        t.gstin = gstin
        if 'address' in request.data:
            t.address = str(request.data['address']).strip()[:500]
        if 'phone' in request.data:
            t.phone = str(request.data['phone']).strip()[:20]
        t.save(update_fields=['gstin', 'address', 'phone'])
        return Response({'name': t.name, 'gstin': t.gstin, 'address': t.address, 'phone': t.phone})
