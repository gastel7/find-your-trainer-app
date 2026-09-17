import json
from django.test import TestCase
from django.urls import reverse

from account.models import User
from notifications.models import Notification, PushSubscription
from notifications.services import notifier_utilisateur


class NotifierUtilisateurTestCase(TestCase):
    """Le point d'entrée central utilisé par tout le reste de l'app."""

    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='x', role='formateur')

    def test_cree_une_notification_in_app(self):
        notifier_utilisateur(self.user, titre="Titre", message="Message", url="/quelque-part/")
        self.assertTrue(Notification.objects.filter(user=self.user, titre="Titre").exists())

    def test_sans_abonnement_push_ne_plante_pas(self):
        # Aucun PushSubscription enregistré : ne doit lever aucune exception.
        notifier_utilisateur(self.user, titre="Titre", message="Message")
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)


class NotificationsViewsTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='x', role='formateur')
        self.client.force_login(self.user)

        self.notif1 = Notification.objects.create(user=self.user, titre="Notif 1")
        self.notif2 = Notification.objects.create(user=self.user, titre="Notif 2", lue=True)

    def test_liste_notifications_compte_les_non_lues(self):
        response = self.client.get(reverse('notifications:liste'))
        data = response.json()
        self.assertEqual(data['non_lues'], 1)
        self.assertEqual(len(data['notifications']), 2)

    def test_marquer_lu(self):
        self.client.post(reverse('notifications:marquer_lu', args=[self.notif1.id]))
        self.notif1.refresh_from_db()
        self.assertTrue(self.notif1.lue)

    def test_marquer_tout_lu(self):
        self.client.post(reverse('notifications:marquer_tout_lu'))
        self.assertEqual(Notification.objects.filter(user=self.user, lue=False).count(), 0)

    def test_on_ne_voit_pas_les_notifications_dun_autre(self):
        autre = User.objects.create_user(username='bob', password='x', role='formateur')
        Notification.objects.create(user=autre, titre="Pas pour toi")

        response = self.client.get(reverse('notifications:liste'))
        titres = [n['titre'] for n in response.json()['notifications']]
        self.assertNotIn("Pas pour toi", titres)


class PushSubscriptionTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='x', role='formateur')
        self.client.force_login(self.user)

    def test_enregistrement_abonnement(self):
        payload = {
            "endpoint": "https://push.example.com/abc123",
            "keys": {"p256dh": "clepublique", "auth": "clesecrete"},
        }
        self.client.post(
            reverse('notifications:save_push_subscription'),
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertTrue(PushSubscription.objects.filter(user=self.user, endpoint=payload['endpoint']).exists())

    def test_abonnement_incomplet_refuse(self):
        payload = {"endpoint": "https://push.example.com/incomplet"}
        response = self.client.post(
            reverse('notifications:save_push_subscription'),
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(PushSubscription.objects.filter(endpoint=payload['endpoint']).exists())