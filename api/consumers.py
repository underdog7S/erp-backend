import json
from channels.generic.websocket import AsyncWebsocketConsumer

class InboxConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.tenant_slug = self.scope['url_route']['kwargs']['tenant_slug']
        self.room_group_name = f'inbox_{self.tenant_slug}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from room group
    async def new_message(self, event):
        message_data = event['message_data']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message_data': message_data
        }))
