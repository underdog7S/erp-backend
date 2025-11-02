from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone
from django.db.models import Q, Count
from datetime import timedelta

from api.models.user import UserProfile
from api.models.notifications import (
    Notification, NotificationPreference, NotificationTemplate, NotificationLog
)
from api.serializers import (
    NotificationSerializer, NotificationPreferenceSerializer,
    NotificationTemplateSerializer, NotificationStatsSerializer
)


class NotificationListView(APIView):
    """
    Get list of notifications for the current user
    Supports filtering by module, type, read status, and pagination
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            notifications = Notification.objects.filter(user=request.user, tenant=profile.tenant)
            
            # Filter by read status
            read_filter = request.query_params.get('read')
            if read_filter is not None:
                read_bool = read_filter.lower() == 'true'
                notifications = notifications.filter(read=read_bool)
            
            # Filter by module
            module = request.query_params.get('module')
            if module:
                notifications = notifications.filter(module=module)
            
            # Filter by type
            notification_type = request.query_params.get('type')
            if notification_type:
                notifications = notifications.filter(notification_type=notification_type)
            
            # Filter by priority
            priority = request.query_params.get('priority')
            if priority:
                notifications = notifications.filter(priority=priority)
            
            # Exclude expired notifications
            exclude_expired = request.query_params.get('exclude_expired', 'true').lower() == 'true'
            if exclude_expired:
                notifications = notifications.filter(
                    Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
                )
            
            # Order by created_at (newest first)
            notifications = notifications.order_by('-created_at')
            
            # Pagination
            page_size = int(request.query_params.get('page_size', 20))
            page = int(request.query_params.get('page', 1))
            start = (page - 1) * page_size
            end = start + page_size
            
            total_count = notifications.count()
            paginated_notifications = notifications[start:end]
            
            serializer = NotificationSerializer(paginated_notifications, many=True)
            
            return Response({
                'notifications': serializer.data,
                'total_count': total_count,
                'page': page,
                'page_size': page_size,
                'has_next': end < total_count,
                'has_previous': page > 1
            })
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotificationDetailView(APIView):
    """
    Get, update, or delete a specific notification
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, notification_id):
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            serializer = NotificationSerializer(notification)
            return Response(serializer.data)
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, notification_id):
        """Update notification (mainly for marking as read/unread)"""
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            
            # Mark as read
            if 'read' in request.data:
                read_value = request.data.get('read')
                if read_value:
                    notification.mark_as_read()
                else:
                    notification.read = False
                    notification.read_at = None
                    notification.save(update_fields=['read', 'read_at'])
            
            serializer = NotificationSerializer(notification)
            return Response(serializer.data)
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, notification_id):
        """Delete a notification"""
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            notification.delete()
            return Response({'message': 'Notification deleted successfully.'})
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotificationMarkReadView(APIView):
    """
    Mark notification(s) as read
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            notification_ids = request.data.get('notification_ids', [])
            if not notification_ids:
                return Response({'error': 'notification_ids is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not isinstance(notification_ids, list):
                notification_ids = [notification_ids]
            
            notifications = Notification.objects.filter(
                id__in=notification_ids,
                user=request.user
            )
            
            updated_count = 0
            for notification in notifications:
                if not notification.read:
                    notification.mark_as_read()
                    updated_count += 1
            
            return Response({
                'message': f'{updated_count} notification(s) marked as read.',
                'updated_count': updated_count
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotificationMarkAllReadView(APIView):
    """
    Mark all unread notifications as read
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            notifications = Notification.objects.filter(
                user=request.user,
                tenant=profile.tenant,
                read=False
            )
            
            updated_count = 0
            for notification in notifications:
                notification.mark_as_read()
                updated_count += 1
            
            return Response({
                'message': f'{updated_count} notification(s) marked as read.',
                'updated_count': updated_count
            })
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotificationStatsView(APIView):
    """
    Get notification statistics for the current user
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            notifications = Notification.objects.filter(user=request.user, tenant=profile.tenant)
            
            # Exclude expired
            notifications = notifications.filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
            )
            
            total = notifications.count()
            unread = notifications.filter(read=False).count()
            
            # Count by type
            by_type = {}
            for notif_type, label in Notification.NOTIFICATION_TYPES:
                count = notifications.filter(notification_type=notif_type).count()
                if count > 0:
                    by_type[notif_type] = count
            
            # Count by module
            by_module = {}
            for module, label in Notification.MODULE_CHOICES:
                count = notifications.filter(module=module).count()
                if count > 0:
                    by_module[module] = count
            
            # Count by priority
            by_priority = {}
            for priority, label in Notification.PRIORITY_LEVELS:
                count = notifications.filter(priority=priority).count()
                if count > 0:
                    by_priority[priority] = count
            
            # Recent notifications (last 24 hours)
            recent_count = notifications.filter(
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).count()
            
            stats = {
                'total': total,
                'unread': unread,
                'by_type': by_type,
                'by_module': by_module,
                'by_priority': by_priority,
                'recent_count': recent_count
            }
            
            serializer = NotificationStatsSerializer(stats)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotificationPreferenceView(APIView):
    """
    Get or update user's notification preferences
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            preference, created = NotificationPreference.objects.get_or_create(
                user=request.user,
                defaults={'tenant': profile.tenant}
            )
            serializer = NotificationPreferenceSerializer(preference)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        """Update notification preferences"""
        try:
            profile = UserProfile.objects.get(user=request.user)
            preference, created = NotificationPreference.objects.get_or_create(
                user=request.user,
                defaults={'tenant': profile.tenant}
            )
            
            serializer = NotificationPreferenceSerializer(preference, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotificationBulkDeleteView(APIView):
    """
    Delete multiple notifications
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            notification_ids = request.data.get('notification_ids', [])
            if not notification_ids:
                return Response({'error': 'notification_ids is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not isinstance(notification_ids, list):
                notification_ids = [notification_ids]
            
            notifications = Notification.objects.filter(
                id__in=notification_ids,
                user=request.user
            )
            
            deleted_count = notifications.count()
            notifications.delete()
            
            return Response({
                'message': f'{deleted_count} notification(s) deleted successfully.',
                'deleted_count': deleted_count
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

