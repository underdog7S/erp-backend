import logging
from django.db.models import Q, Max
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status
from django.contrib.auth.models import User
from api.models.user import UserProfile
from api.models.team_chat import ChatChannel, ChatChannelMembership, ChatMessage

logger = logging.getLogger(__name__)


def _channel_display(channel, membership_user):
    """Name + other-member info for a channel, from membership_user's point of view."""
    if channel.channel_type == 'group':
        return channel.name or 'Group'
    other = ChatChannelMembership.objects.filter(channel=channel).exclude(user=membership_user).select_related('user').first()
    if other and other.user:
        return other.user.get_full_name() or other.user.username
    return channel.name or 'Direct Message'


class ChannelListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = ChatChannelMembership.objects.filter(user=request.user).select_related('channel')
        data = []
        for m in memberships:
            channel = m.channel
            last_msg = channel.messages.order_by('-created_at').first()
            unread_count = channel.messages.filter(created_at__gt=m.last_read_at).count() if m.last_read_at else channel.messages.count()
            data.append({
                'id': channel.id,
                'name': _channel_display(channel, request.user),
                'channel_type': channel.channel_type,
                'last_message': last_msg.content if last_msg else None,
                'last_message_at': last_msg.created_at if last_msg else channel.created_at,
                'unread_count': unread_count,
            })
        data.sort(key=lambda c: c['last_message_at'], reverse=True)
        return Response(data)

    def post(self, request):
        """Create a group channel. { name, member_ids: [...] }"""
        profile = UserProfile.objects.get(user=request.user)
        name = request.data.get('name', '').strip()
        member_ids = request.data.get('member_ids', [])
        if not name:
            return Response({'error': 'Group name is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not member_ids:
            return Response({'error': 'Select at least one other member'}, status=status.HTTP_400_BAD_REQUEST)

        # Only allow adding members from the same tenant.
        members = User.objects.filter(id__in=member_ids, userprofile__tenant=profile.tenant)

        channel = ChatChannel.objects.create(tenant=profile.tenant, name=name, channel_type='group', created_by=request.user)
        ChatChannelMembership.objects.create(channel=channel, user=request.user)
        for member in members:
            ChatChannelMembership.objects.get_or_create(channel=channel, user=member)

        return Response({'id': channel.id, 'name': channel.name, 'channel_type': 'group'}, status=status.HTTP_201_CREATED)


class DirectMessageView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        """Get-or-create a 1:1 channel between request.user and user_id."""
        profile = UserProfile.objects.get(user=request.user)
        try:
            other_user = User.objects.get(id=user_id, userprofile__tenant=profile.tenant)
        except User.DoesNotExist:
            return Response({'error': 'User not found in your organization'}, status=status.HTTP_404_NOT_FOUND)

        if other_user.id == request.user.id:
            return Response({'error': "Can't start a conversation with yourself"}, status=status.HTTP_400_BAD_REQUEST)

        existing = ChatChannel.objects.filter(
            tenant=profile.tenant, channel_type='direct', memberships__user=request.user
        ).filter(memberships__user=other_user).first()

        if existing:
            return Response({'id': existing.id, 'name': _channel_display(existing, request.user), 'channel_type': 'direct'})

        channel = ChatChannel.objects.create(tenant=profile.tenant, channel_type='direct', created_by=request.user)
        ChatChannelMembership.objects.create(channel=channel, user=request.user)
        ChatChannelMembership.objects.create(channel=channel, user=other_user)

        return Response({'id': channel.id, 'name': _channel_display(channel, request.user), 'channel_type': 'direct'}, status=status.HTTP_201_CREATED)


class ChannelMessagesView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_membership(self, request, channel_id):
        return ChatChannelMembership.objects.filter(channel_id=channel_id, user=request.user).select_related('channel').first()

    def get(self, request, channel_id):
        membership = self._get_membership(request, channel_id)
        if not membership:
            return Response({'error': 'Not a member of this channel'}, status=status.HTTP_403_FORBIDDEN)

        messages = membership.channel.messages.select_related('sender').order_by('created_at')
        data = [{
            'id': m.id,
            'content': m.content,
            'sender_id': m.sender_id,
            'sender_name': (m.sender.get_full_name() or m.sender.username) if m.sender else 'Deleted user',
            'is_mine': m.sender_id == request.user.id,
            'created_at': m.created_at,
        } for m in messages]
        return Response(data)

    def post(self, request, channel_id):
        membership = self._get_membership(request, channel_id)
        if not membership:
            return Response({'error': 'Not a member of this channel'}, status=status.HTTP_403_FORBIDDEN)

        content = (request.data.get('content') or '').strip()
        if not content:
            return Response({'error': 'Message content is required'}, status=status.HTTP_400_BAD_REQUEST)

        message = ChatMessage.objects.create(channel=membership.channel, sender=request.user, content=content)
        membership.last_read_at = message.created_at
        membership.save(update_fields=['last_read_at'])

        return Response({
            'id': message.id,
            'content': message.content,
            'sender_id': message.sender_id,
            'sender_name': request.user.get_full_name() or request.user.username,
            'is_mine': True,
            'created_at': message.created_at,
        }, status=status.HTTP_201_CREATED)


class MarkChannelReadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, channel_id):
        membership = ChatChannelMembership.objects.filter(channel_id=channel_id, user=request.user).first()
        if not membership:
            return Response({'error': 'Not a member of this channel'}, status=status.HTTP_403_FORBIDDEN)
        membership.last_read_at = timezone.now()
        membership.save(update_fields=['last_read_at'])
        return Response({'status': 'ok'})
