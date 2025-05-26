import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import ChatRoom
from django.shortcuts import get_object_or_404
from asgiref.sync import sync_to_async # For database operations



class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Super simple print to see if this method is EVER called
        print("!!!!!! CHAT CONSUMER CONNECT METHOD CALLED !!!!!!")
        # await self.accept() # Moved accept after successful room check
        # print("!!!!!! CHAT CONSUMER CONNECTION ACCEPTED !!!!!!")

        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        print(f"ChatConsumer: Attempting to connect. Room ID: {self.room_id}")

        try:
            self.chat_room = await sync_to_async(ChatRoom.objects.get)(room_id=self.room_id, is_active=True)
            print(f"ChatConsumer: Found active chat room: {self.chat_room}")
        except ChatRoom.DoesNotExist:
            print(f"ChatConsumer: Chat room {self.room_id} does not exist or is not active. Closing connection.")
            await self.close()
            return

        await self.accept() # Accept connection only if room is valid
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        print(f"ChatConsumer: WebSocket connected and added to group {self.room_group_name}")

    async def disconnect(self, close_code):
        print(f"ChatConsumer: WebSocket disconnected with code {close_code}. Leaving group {self.room_group_name}")
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        print(f"ChatConsumer: Received raw message: {text_data}")
        try:
            text_data_json = json.loads(text_data)
            message_content = text_data_json['message']
            username = text_data_json.get('username', 'Anonymous')
            print(f"ChatConsumer: Parsed message: '{message_content}' from user: '{username}'")

            if hasattr(self, 'chat_room') and message_content == self.chat_room.deletion_phrase:
                print(f"ChatConsumer: Deletion phrase received. Handling room deletion.")
                await self.handle_room_deletion()
                return

            print(f"ChatConsumer: Sending message to group {self.room_group_name}")
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message_content,
                    'username': username
                }
            )
        except json.JSONDecodeError:
            print(f"ChatConsumer: Failed to decode JSON from received message: {text_data}")
        except KeyError:
            print(f"ChatConsumer: 'message' key not found in received JSON: {text_data_json}")


    async def chat_message(self, event):
        message = event['message']
        username = event.get('username', 'System')
        print(f"ChatConsumer: chat_message handler received event for group. Message: '{message}' from '{username}'. Sending to client.")
        await self.send(text_data=json.dumps({
            'message': message,
            'username': username
        }))
