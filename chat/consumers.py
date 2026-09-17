import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from .models import Message
from account.models import User


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]
        self.destinataire_id = self.scope['url_route']['kwargs']['user_id']

        ids = sorted([str(self.user.id), str(self.destinataire_id)])
        self.room_group_name = f"chat_{ids[0]}_{ids[1]}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        print("✅ WebSocket connecté")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        print("❌ WebSocket déconnecté")

    async def receive(self, text_data):
        data = json.loads(text_data)

        # --- CAS 1 : ACTION DE SUPPRESSION D'UN MESSAGE ---
        if data.get('action') == 'delete_message':
            message_id = data.get('message_id')
            await self.mark_message_as_deleted(message_id)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message_delete',
                    'message_id': message_id,
                }
            )
            return

        # --- CAS 2 : RÉCEPTION D'UN NOUVEAU MESSAGE (Texte ou Média) ---
        message_contenu = data.get('message', '')
        file_url = data.get('file_url', None)
        file_type = data.get('file_type', None)
        message_id = data.get('message_id', None)

        # Si le message vient du bouton d'upload HTTP (image/vocal), l'objet BDD existe déjà.
        # Sinon, s'il s'agit d'un bête message texte, on le crée ici en BDD.
        if not message_id:
            message_obj = await self.save_message(message_contenu)
            message_id = message_obj.id

        # Envoi en temps réel à l'autre utilisateur via le groupe
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_contenu,
                'message_id': message_id,
                'file_url': file_url,
                'file_type': file_type,
                'sender_id': self.user.id,
                'sender_username': self.user.username,
            }
        )

    # Diffusion de l'affichage (On passe bien toutes les variables au JavaScript)
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event.get('message', ''),
            'message_id': event.get('message_id'),
            'file_url': event.get('file_url'),
            'file_type': event.get('file_type'),
            'sender_id': event.get('sender_id'),
            'sender_username': event.get('sender_username'),
        }))

    async def chat_message_delete(self, event):
        await self.send(text_data=json.dumps({
            'action': 'message_deleted',
            'message_id': event['message_id'],
        }))

    @database_sync_to_async
    def save_message(self, message):
        from django.urls import reverse
        from notifications.services import notifier_utilisateur

        destinataire = User.objects.get(id=self.destinataire_id)
        message_obj = Message.objects.create(
            expediteur_id=self.user,
            destinataire_id=destinataire,
            contenu=message
        )

        # Aperçu tronqué du message dans la notification (pas tout le texte)
        apercu = message[:80] + ('…' if len(message) > 80 else '')
        notifier_utilisateur(
            destinataire,
            titre=f"Nouveau message de {self.user.username}",
            message=apercu,
            url=reverse('chat:chat_room', args=[self.user.id]),
        )

        return message_obj

    @database_sync_to_async
    def mark_message_as_deleted(self, message_id):
        try:
            int_id = int(message_id)
            return Message.objects.filter(id=int_id, expediteur_id=self.user).update(is_delete=True)
        except (ValueError, TypeError):
            return 0