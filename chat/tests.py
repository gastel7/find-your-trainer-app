from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from account.models import User
from chat.models import Message


class MessageModelTestCase(TestCase):

    def setUp(self):
        self.alice = User.objects.create_user(username='alice', password='x', role='formateur')
        self.bob = User.objects.create_user(username='bob', password='x', role='formateur')

    def test_message_texte_simple(self):
        message = Message.objects.create(expediteur_id=self.alice, destinataire_id=self.bob, contenu='Salut !')
        self.assertEqual(message.file_type, None)
        self.assertFalse(message.is_read)

    def test_file_type_image(self):
        fichier = SimpleUploadedFile('photo.jpg', b'contenu factice', content_type='image/jpeg')
        message = Message.objects.create(expediteur_id=self.alice, destinataire_id=self.bob, fichier_joint=fichier)
        self.assertEqual(message.file_type, 'image')

    def test_file_type_document_par_defaut(self):
        fichier = SimpleUploadedFile('cv.pdf', b'contenu factice', content_type='application/pdf')
        message = Message.objects.create(expediteur_id=self.alice, destinataire_id=self.bob, fichier_joint=fichier)
        self.assertEqual(message.file_type, 'document')


class ChatViewTestCase(TestCase):

    def setUp(self):
        self.alice = User.objects.create_user(username='alice', password='x', role='formateur')
        self.bob = User.objects.create_user(username='bob', password='x', role='formateur')
        self.client.force_login(self.alice)

    def test_acces_chat_accueil(self):
        response = self.client.get(reverse('chat:chat_accueil'))
        self.assertEqual(response.status_code, 200)

    def test_acces_conversation_precise(self):
        response = self.client.get(reverse('chat:chat_room', args=[self.bob.id]))
        self.assertEqual(response.status_code, 200)

    def test_anonyme_redirige_vers_login(self):
        self.client.logout()
        response = self.client.get(reverse('chat:chat_accueil'))
        self.assertEqual(response.status_code, 302)