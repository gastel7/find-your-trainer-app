import datetime
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from account.models import User, Formateur
from formation.models import Formation, InscriptionFormation


class FormationProprietesTestCase(TestCase):
    """Les @property calculées : est_terminee, est_complete, places_restantes, duree."""

    def setUp(self):
        user = User.objects.create_user(username='prof', password='x', role='formateur')
        self.formateur = Formateur.objects.create(user=user)

    def _creer_formation(self, date_debut, date_cloture, nb_places_max=2, terminee_manuelle=False):
        return Formation.objects.create(
            formateur=self.formateur,
            titre='Formation test',
            description='...',
            categorie='developpement',
            niveau='debutant',
            prix=100,
            date_debut=date_debut,
            date_cloture=date_cloture,
            nb_places_max=nb_places_max,
            terminee_manuelle=terminee_manuelle,
        )

    def test_duree_un_jour(self):
        formation = self._creer_formation(datetime.date(2026, 1, 1), datetime.date(2026, 1, 1))
        self.assertEqual(formation.duree, "1 jour")

    def test_duree_plusieurs_jours(self):
        formation = self._creer_formation(datetime.date(2026, 1, 1), datetime.date(2026, 1, 4))
        self.assertEqual(formation.duree, "4 jours")

    def test_est_terminee_si_date_passee(self):
        formation = self._creer_formation(
            timezone.now().date() - datetime.timedelta(days=10),
            timezone.now().date() - datetime.timedelta(days=5),
        )
        self.assertTrue(formation.est_terminee)

    def test_nest_pas_terminee_si_date_future(self):
        formation = self._creer_formation(
            timezone.now().date() + datetime.timedelta(days=5),
            timezone.now().date() + datetime.timedelta(days=10),
        )
        self.assertFalse(formation.est_terminee)

    def test_terminee_manuelle_prime_sur_la_date(self):
        formation = self._creer_formation(
            timezone.now().date() + datetime.timedelta(days=30),
            timezone.now().date() + datetime.timedelta(days=31),
            terminee_manuelle=True,
        )
        self.assertTrue(formation.est_terminee)

    def test_places_restantes_et_complete(self):
        formation = self._creer_formation(None, None, nb_places_max=1)
        self.assertEqual(formation.places_restantes, 1)
        self.assertFalse(formation.est_complete)

        participant = User.objects.create_user(username='part1', password='x', role='formateur')
        InscriptionFormation.objects.create(formation=formation, participant=participant)

        self.assertEqual(formation.places_restantes, 0)
        self.assertTrue(formation.est_complete)

    def test_une_seule_date_complete_lautre(self):
        formation = self._creer_formation(datetime.date(2026, 3, 1), None)
        self.assertEqual(formation.date_cloture, datetime.date(2026, 3, 1))


class InscriptionFormationTestCase(TestCase):
    """Le flux d'inscription/désinscription et ses règles métier."""

    def setUp(self):
        formateur_user = User.objects.create_user(username='prof', password='x', role='formateur')
        self.formateur = Formateur.objects.create(user=formateur_user)

        self.participant = User.objects.create_user(username='eleve', password='x', role='formateur')
        Formateur.objects.create(user=self.participant)

        self.formation = Formation.objects.create(
            formateur=self.formateur,
            titre='Formation React',
            description='...',
            categorie='developpement',
            niveau='debutant',
            prix=100,
            nb_places_max=1,
        )

        self.client.force_login(self.participant)

    def test_inscription_reussie(self):
        response = self.client.post(reverse('formation:inscription_formation', args=[self.formation.id]))
        self.assertTrue(
            InscriptionFormation.objects.filter(formation=self.formation, participant=self.participant).exists()
        )

    def test_double_inscription_refusee(self):
        InscriptionFormation.objects.create(formation=self.formation, participant=self.participant)
        self.client.post(reverse('formation:inscription_formation', args=[self.formation.id]))
        self.assertEqual(
            InscriptionFormation.objects.filter(formation=self.formation, participant=self.participant).count(), 1
        )

    def test_formateur_principal_ne_peut_pas_sinscrire_a_sa_propre_formation(self):
        client_formateur = self.client_class()
        client_formateur.force_login(self.formateur.user)
        client_formateur.post(reverse('formation:inscription_formation', args=[self.formation.id]))
        self.assertFalse(
            InscriptionFormation.objects.filter(formation=self.formation, participant=self.formateur.user).exists()
        )

    def test_inscription_refusee_si_formation_complete(self):
        autre_participant = User.objects.create_user(username='eleve2', password='x', role='formateur')
        InscriptionFormation.objects.create(formation=self.formation, participant=autre_participant)

        self.client.post(reverse('formation:inscription_formation', args=[self.formation.id]))
        self.assertFalse(
            InscriptionFormation.objects.filter(formation=self.formation, participant=self.participant).exists()
        )

    def test_desinscription(self):
        InscriptionFormation.objects.create(formation=self.formation, participant=self.participant)
        self.client.post(reverse('formation:desinscription_formation', args=[self.formation.id]))
        self.assertFalse(
            InscriptionFormation.objects.filter(formation=self.formation, participant=self.participant).exists()
        )