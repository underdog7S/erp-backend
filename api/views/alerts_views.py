from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models.alerts import Alert
from api.models.user import UserProfile
from api.models.permissions import role_required
from django.utils import timezone
from django.db import transaction
from api.utils.alert_utils import (
    create_alert, create_usage_alert, create_plan_expiry_alert,
    bulk_create_alerts, cleanup_old_alerts, get_alert_summary,
    mark_alerts_read, mark_alerts_unread, delete_alerts
)

class AlertListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            alerts = Alert.objects.filter(tenant=profile.tenant).order_by('-created_at')
            
            # Add pagination support
            page_size = int(request.query_params.get('page_size', 20))
            page = int(request.query_params.get('page', 1))
            start = (page - 1) * page_size
            end = start + page_size
            
            paginated_alerts = alerts[start:end]
            
            data = [
                {
                    'id': a.id,
                    'message': a.message,
                    'type': a.type,
                    'created_at': a.created_at,
                    'read': a.read
                } for a in paginated_alerts
            ]
            
            return Response({
                'alerts': data,
                'total_count': alerts.count(),
                'page': page,
                'page_size': page_size,
                'has_next': end < alerts.count(),
                'has_previous': page > 1
            })
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AlertMarkReadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            alert_id = request.data.get('alert_id')
            read = request.data.get('read', True)
            
            if not alert_id:
                return Response({'error': 'alert_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                alert = Alert.objects.get(id=alert_id, tenant=profile.tenant)
                alert.read = read
                alert.save()
                return Response({'message': 'Alert updated successfully.', 'alert_id': alert.id})
            except Alert.DoesNotExist:
                return Response({'error': 'Alert not found.'}, status=status.HTTP_404_NOT_FOUND)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AlertCreateView(APIView):
    """Create new alerts - Admin only"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @role_required('admin', 'principal')
    def post(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            message = request.data.get('message')
            alert_type = request.data.get('type', 'general')
            
            if not message:
                return Response({'error': 'Message is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if alert_type not in [choice[0] for choice in Alert.ALERT_TYPES]:
                return Response({'error': 'Invalid alert type.'}, status=status.HTTP_400_BAD_REQUEST)
            
            alert = Alert.objects.create(
                tenant=profile.tenant,
                message=message,
                type=alert_type
            )
            
            return Response({
                'message': 'Alert created successfully.',
                'alert': {
                    'id': alert.id,
                    'message': alert.message,
                    'type': alert.type,
                    'created_at': alert.created_at,
                    'read': alert.read
                }
            }, status=status.HTTP_201_CREATED)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AlertDeleteView(APIView):
    """Delete alerts - Admin only"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @role_required('admin', 'principal')
    def delete(self, request, alert_id):
        try:
            profile = UserProfile.objects.get(user=request.user)
            
            try:
                alert = Alert.objects.get(id=alert_id, tenant=profile.tenant)
                alert.delete()
                return Response({'message': 'Alert deleted successfully.'})
            except Alert.DoesNotExist:
                return Response({'error': 'Alert not found.'}, status=status.HTTP_404_NOT_FOUND)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AlertBulkMarkReadView(APIView):
    """Mark multiple alerts as read/unread"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            alert_ids = request.data.get('alert_ids', [])
            read = request.data.get('read', True)
            
            if not alert_ids:
                return Response({'error': 'alert_ids is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not isinstance(alert_ids, list):
                return Response({'error': 'alert_ids must be a list.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Use utility function
            if read:
                updated_count = mark_alerts_read(profile.tenant, alert_ids)
            else:
                updated_count = mark_alerts_unread(profile.tenant, alert_ids)
            
            return Response({
                'message': f'{updated_count} alerts updated successfully.',
                'updated_count': updated_count
            })
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AlertBulkDeleteView(APIView):
    """Delete multiple alerts - Admin only"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @role_required('admin', 'principal')
    def post(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            alert_ids = request.data.get('alert_ids', [])
            
            if not alert_ids:
                return Response({'error': 'alert_ids is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not isinstance(alert_ids, list):
                return Response({'error': 'alert_ids must be a list.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Use utility function
            deleted_count = delete_alerts(profile.tenant, alert_ids)
            
            return Response({
                'message': f'{deleted_count} alerts deleted successfully.',
                'deleted_count': deleted_count
            })
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AlertStatsView(APIView):
    """Get alert statistics for dashboard"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            tenant = profile.tenant
            
            # Use utility function for alert summary
            summary = get_alert_summary(tenant)
            return Response(summary)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AlertAutoCreateView(APIView):
    """Auto-create alerts based on system conditions - Internal use"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @role_required('admin', 'principal')
    def post(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            tenant = profile.tenant
            
            alerts_created = []
            
            # Check storage usage
            if tenant.plan:
                storage_limit_mb = tenant.plan.storage_limit_mb
                if tenant.storage_used_mb > storage_limit_mb * 0.9:  # 90% threshold
                    alert = create_usage_alert(
                        tenant, 
                        'storage', 
                        tenant.storage_used_mb, 
                        storage_limit_mb, 
                        'MB'
                    )
                    alerts_created.append(alert.id)
                
                # Check user limit
                current_users = UserProfile.objects.filter(tenant=tenant).count()
                if tenant.plan.max_users and current_users >= tenant.plan.max_users * 0.9:  # 90% threshold
                    alert = create_usage_alert(
                        tenant,
                        'users',
                        current_users,
                        tenant.plan.max_users,
                        ' users'
                    )
                    alerts_created.append(alert.id)
            
            return Response({
                'message': 'Auto-alerts check completed.',
                'alerts_created': len(alerts_created),
                'alert_ids': alerts_created
            })
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AlertCleanupView(APIView):
    """Clean up old alerts - Admin only"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @role_required('admin', 'principal')
    def post(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            tenant = profile.tenant
            days_old = request.data.get('days_old', 30)
            
            if not isinstance(days_old, int) or days_old < 1:
                return Response({'error': 'days_old must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Use utility function
            deleted_count = cleanup_old_alerts(tenant, days_old)
            
            return Response({
                'message': f'{deleted_count} old alerts cleaned up successfully.',
                'deleted_count': deleted_count,
                'days_old': days_old
            })
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)