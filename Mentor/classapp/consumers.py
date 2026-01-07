import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

class EventChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.event_id = self.scope['url_route']['kwargs']['event_id']
        self.room_group_name = f"event_chat_{self.event_id}"
        self.user = self.scope.get("user")
        self.user_identity = self.user.username if self.user.is_authenticated else "Guest_Node"

        # Join Event Cluster
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Feature 1: System Handshake Notification
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "system_message",
                "payload": {
                    "type": "CONNECTION_ESTABLISHED",
                    "user": self.user_identity,
                    "message": f"User {self.user_identity} synchronized with Node {self.event_id}",
                    "timestamp": timezone.now().strftime("%H:%M:%S")
                }
            }
        )

    async def disconnect(self, close_code):
        # Feature 2: Graceful Termination Handshake
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """Processes incoming data nodes from the client."""
        data = json.loads(text_data)
        message_type = data.get("type", "CHAT_MESSAGE") # Default type
        message = data.get("message")

        # Feature 3: Metadata Handshake (Adding avatars/timestamps)
        payload = {
            "type": message_type,
            "user": self.user_identity,
            "message": message,
            "avatar_node": f"https://i.pravatar.cc/100?u={self.user_identity}",
            "timestamp": timezone.now().strftime("%H:%M:%S")
        }

        # Dispatch to Node Cluster
        await self.channel_layer.group_send(
            self.room_group_name, 
            {"type": "chat_message", "payload": payload}
        )

    # Handlers for different broadcast types
    async def chat_message(self, event):
        """Standard Chat Relay"""
        await self.send(text_data=json.dumps(event["payload"]))

    async def system_message(self, event):
        """Feature 4: System Alerts (Triggers UI Glows)"""
        await self.send(text_data=json.dumps({
            "type": "SYSTEM_ALERT",
            "payload": event["payload"]
        }))