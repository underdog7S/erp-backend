"""Edit and delete for the academic setup records (terms, subjects, assessments) that only had list/create routes."""
from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from api.models.permissions import HasFeaturePermissionFactory, role_required
from api.models.serializers_education import AssessmentSerializer, SubjectSerializer, TermSerializer
from education.models import Assessment, Subject, Term


class _TenantDetail(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    model = None
    serializer_class = None

    def _obj(self, request, pk):
        return self.model._default_manager.filter(pk=pk, tenant=request.user.userprofile.tenant).first()

    def get(self, request, pk):
        obj = self._obj(request, pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.serializer_class(obj).data)

    def _save(self, request, pk, partial):
        obj = self._obj(request, pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        data = request.data.copy()
        data['tenant'] = obj.tenant_id
        ser = self.serializer_class(obj, data=data, partial=partial)
        if ser.is_valid():
            ser.save(tenant=obj.tenant)
            return Response(ser.data)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    @role_required('admin', 'principal')
    def put(self, request, pk):
        return self._save(request, pk, False)

    @role_required('admin', 'principal')
    def patch(self, request, pk):
        return self._save(request, pk, True)

    @role_required('admin', 'principal')
    def delete(self, request, pk):
        obj = self._obj(request, pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            obj.delete()
        except ProtectedError:
            return Response({'error': 'This is in use (marks, exams or fees refer to it), so it cannot be deleted.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TermDetailView(_TenantDetail):
    model, serializer_class = Term, TermSerializer


class SubjectDetailView(_TenantDetail):
    model, serializer_class = Subject, SubjectSerializer


class AssessmentDetailView(_TenantDetail):
    model, serializer_class = Assessment, AssessmentSerializer
