from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models.alerts import Alert
from api.models.user import UserProfile

class AlertListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserProfile.objects.get(user=request.user)
        alerts = Alert.objects.filter(tenant=profile.tenant).order_by('-created_at')
        data = [
            {
                'id': a.id,
                'message': a.message,
                'type': a.type,
                'created_at': a.created_at,
                'read': a.read
            } for a in alerts
        ]
        return Response(data)

class AlertMarkReadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = UserProfile.objects.get(user=request.user)
        alert_id = request.data.get('alert_id')
        read = request.data.get('read', True)
        try:
            alert = Alert.objects.get(id=alert_id, tenant=profile.tenant)
            alert.read = read
            alert.save()
            return Response({'message': 'Alert updated.'})
        except Alert.DoesNotExist:
            return Response({'error': 'Alert not found.'}, status=status.HTTP_404_NOT_FOUND) 