from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse

from account.models import User
from support.models import SupportTicket
from support.services import GestSupAPIError
from notifications.models import Notification


class CreerDemandeAideTestCase(TestCase):
    """L'appel réel à GestSup est simulé (mock) : ces tests ne contactent
    jamais un vrai serveur GestSup — rapides et fiables à chaque lancement."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', password='x', role='formateur', email='alice@test.com'
        )
        self.admin = User.objects.create_superuser(username='boss', password='x', email='boss@test.com')
        self.client.force_login(self.user)

    @patch('support.views.create_gestsup_ticket')
    def test_creation_reussie(self, mock_create):
        mock_create.return_value = {'code': 0, 'ticket_id': '42', 'ticket_url': 'http://gestsup/ticket/42'}

        response = self.client.post(reverse('support:creer_demande_aide'), {
            'titre': 'Bug connexion',
            'description': 'Je narrive pas à me connecter',
        })

        self.assertTrue(response.json()['ok'])
        ticket = SupportTicket.objects.get(user=self.user)
        self.assertEqual(ticket.gestsup_ticket_id, '42')
        self.assertEqual(ticket.statut, SupportTicket.STATUT_ENVOYE)

    @patch('support.views.create_gestsup_ticket')
    def test_echec_gestsup_marque_le_ticket_en_erreur(self, mock_create):
        mock_create.side_effect = GestSupAPIError("Impossible de contacter GestSup")

        response = self.client.post(reverse('support:creer_demande_aide'), {
            'titre': 'Bug connexion',
            'description': 'Je narrive pas à me connecter',
        })

        self.assertFalse(response.json()['ok'])
        ticket = SupportTicket.objects.get(user=self.user)
        self.assertEqual(ticket.statut, SupportTicket.STATUT_ERREUR)

    def test_titre_manquant_refuse(self):
        response = self.client.post(reverse('support:creer_demande_aide'), {'description': 'Sans titre'})
        self.assertFalse(response.json()['ok'])
        self.assertFalse(SupportTicket.objects.filter(user=self.user).exists())

    @patch('support.views.create_gestsup_ticket')
    def test_les_admins_sont_notifies(self, mock_create):
        mock_create.return_value = {'code': 0, 'ticket_id': '42', 'ticket_url': 'http://gestsup/ticket/42'}

        self.client.post(reverse('support:creer_demande_aide'), {
            'titre': 'Bug connexion',
            'description': 'Je narrive pas à me connecter',
        })

        self.assertTrue(Notification.objects.filter(user=self.admin, titre="Nouveau signalement").exists())