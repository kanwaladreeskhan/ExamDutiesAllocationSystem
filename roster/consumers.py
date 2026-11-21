import json
from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    # Called when WebSocket client connects
    async def connect(self):
        self.group_name = "notifications"

        # Add client to the notification group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    # Called when WebSocket client disconnects
    async def disconnect(self, close_code):
        # Remove client from the notification group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Handler for 'duty_update' messages sent from backend
    async def duty_update(self, event):
        # Send the message to the client via WebSocket
        await self.send(text_data=json.dumps({
            "type": "duty_update",
            "message": event.get("message", "Your exam duty roster has been updated."),
        }))