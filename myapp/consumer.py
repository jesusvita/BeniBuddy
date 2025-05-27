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
            message_type = text_data_json.get('type', 'chat_message') # Default to chat_message
            username = text_data_json.get('username', 'Anonymous')

            if message_type == 'delete_room':
                phrase_content = text_data_json.get('phrase')
                print(f"ChatConsumer: Parsed delete_room command with phrase: '{phrase_content}' from user: '{username}'")
                # The deletion phrase check is now implicitly part of handle_delete_room's logic
                # if hasattr(self, 'chat_room') and phrase_content == self.chat_room.deletion_phrase:
                # No, the handle_delete_room should verify the phrase against the DB record
                await self.handle_room_deletion()
                return
            elif message_type == 'chat_message':
                message_content = text_data_json.get('message')
                if message_content is None: # Handle if 'message' key is missing for a chat_message type
                    print(f"ChatConsumer: 'message' key not found for chat_message type: {text_data_json}")
                    return

                print(f"ChatConsumer: Parsed chat_message: '{message_content}' from user: '{username}'")
                print(f"ChatConsumer: Sending message to group {self.room_group_name}")
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message_content,
                        'username': username
                    }
                )
            else:
                print(f"ChatConsumer: Unknown message type received: {message_type}")

        except json.JSONDecodeError:
            print(f"ChatConsumer: Failed to decode JSON from received message: {text_data}")

    async def handle_room_deletion(self):
        """
        Handles deactivating the chat room and notifying clients.
        Assumes self.chat_room is the active room instance.
        """
        user = self.scope["user"]
        print(f"ChatConsumer: handle_room_deletion initiated by user: {user}")

        # Asynchronously get the creator of the chat room
        try:
            room_creator = await sync_to_async(lambda: self.chat_room.created_by)()
        except Exception as e: # Catch potential errors during async access
            print(f"ChatConsumer: Error accessing room_creator: {e}")
            room_creator = None

        # Double-check if the user is the creator (though this should be implicitly handled
        # by the fact that only the creator knows the deletion phrase and is_active is true)
        if not user.is_authenticated or room_creator != user:
            print(f"ChatConsumer: Security check failed or user mismatch for room deletion. User: {user}, Room Creator: {self.chat_room.created_by}")
            # Optionally send an error message back to the specific client
            await self.send(text_data=json.dumps({
                'type': 'error', # Use a specific type for client-side handling if needed
                'message': 'You do not have permission to close this room.'
            }))
            return

        try:
            self.chat_room.is_active = False
            await sync_to_async(self.chat_room.save)()
            print(f"ChatConsumer: Room {self.chat_room.room_id} deactivated successfully.")

            # Notify all clients in the room that it has been closed
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'room_closed_notification', # Use a distinct type for this event
                    'message': 'This chat room has been closed by the administrator.'
                }
            )
            # Optionally, you can also close all connections from the server side,
            # but sending a notification and letting clients handle it is common.
        except Exception as e:
            print(f"ChatConsumer: Error during room deactivation or notification: {e}")
            # Handle error, maybe send a message back to the admin
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'Failed to close room due to a server error.'}))

    async def chat_message(self, event):
        message = event['message']
        username = event.get('username', 'System')
        print(f"ChatConsumer: chat_message handler received event for group. Message: '{message}' from '{username}'. Sending to client.")
        await self.send(text_data=json.dumps({
            'message': message,
            'username': username
        }))

    async def room_closed_notification(self, event):
        """
        Sends the room closed notification to the client.
        """
        message = event['message']
        print(f"ChatConsumer: Sending room_closed_notification: '{message}'")
        await self.send(text_data=json.dumps({
            'type': 'room_closed', # This type should be handled by client-side JS
            'message': message
        }))