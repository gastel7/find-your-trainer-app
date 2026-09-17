import datetime
from django.test import TestCase
from django.urls import reverse

from account.models import User, Institution
from offre.models import Offre


class OffreDureeTestCase(TestCase):
    """Le calcul automatique de duree() au save() — cas limites inclus."""

    def setUp(self):
        user = User.objects.create_user(username='inst', password='x', role='institution')
        self.institution = Institution.objects.create(user=user, nom_organisation='Zepeck')

    def _creer_offre(self, date_debut, date_cloture):
        return Offre.objects.create(
            institution_id=self.institution,
            titre='Mission test',
            description='...',
            type_offre='intra',
            date_debut=date_debut,
            date_cloture=date_cloture,
        )

    def test_duree_un_an(self):
        offre = self._creer_offre(datetime.date(2026, 1, 1), datetime.date(2027, 1, 1))
        self.assertEqual(offre.duree, "1 an")

    def test_duree_plusieurs_mois(self):
        offre = self._creer_offre(datetime.date(2026, 1, 1), datetime.date(2026, 4, 1))
        self.assertEqual(offre.duree, "3 mois")

    def test_duree_un_jour(self):
        offre = self._creer_offre(datetime.date(2026, 1, 1), datetime.date(2026, 1, 1))
        self.assertEqual(offre.duree, "1 jour")

    def test_duree_plusieurs_jours(self):
        offre = self._creer_offre(datetime.date(2026, 1, 1), datetime.date(2026, 1, 5))
        self.assertEqual(offre.duree, "4 jours")

    def test_duree_sans_dates(self):
        offre = Offre.objects.create(
            institution_id=self.institution,
            titre='Mission sans dates',
            description='...',
            type_offre='intra',
        )
        self.assertEqual(offre.duree, "Durée non spécifiée")


class OffrePermissionsTestCase(TestCase):
    """Qui a le droit de créer/modifier/supprimer une offre."""

    def setUp(self):
        user_inst = User.objects.create_user(username='inst', password='x', role='institution')
        self.institution = Institution.objects.create(user=user_inst, nom_organisation='Zepeck')

        user_formateur = User.objects.create_user(username='form', password='x', role='formateur')

        self.offre = Offre.objects.create(
            institution_id=self.institution,
            titre='Mission existante',
            description='...',
            type_offre='intra',
        )

        self.client_institution = self.client_class()
        self.client_institution.force_login(user_inst)

        self.client_formateur = self.client_class()
        self.client_formateur.force_login(user_formateur)

    def test_formateur_ne_peut_pas_ajouter_offre(self):
        response = self.client_formateur.get(reverse('offre:ajouter_offre'))
        self.assertRedirects(response, reverse('core:dashboard'))

    def test_institution_peut_ajouter_offre(self):
        response = self.client_institution.get(reverse('offre:ajouter_offre'))
        self.assertEqual(response.status_code, 200)

    def test_formateur_ne_peut_pas_supprimer_offre_dinstitution(self):
        response = self.client_formateur.post(
            reverse('offre:supprimer_offre', args=[self.offre.id])
        )
        # redirigé vers le dashboard, l'offre doit toujours exister
        self.assertTrue(Offre.objects.filter(id=self.offre.id).exists())

    def test_institution_peut_supprimer_sa_propre_offre(self):
        response = self.client_institution.post(
            reverse('offre:supprimer_offre', args=[self.offre.id])
        )
        self.assertFalse(Offre.objects.filter(id=self.offre.id).exists())


class ListOffresTestCase(TestCase):
    """Filtrage de la liste (type, recherche texte)."""

    def setUp(self):
        user_inst = User.objects.create_user(username='inst', password='x', role='institution')
        self.institution = Institution.objects.create(user=user_inst, nom_organisation='Zepeck Services')

        self.client.force_login(user_inst)

        Offre.objects.create(
            institution_id=self.institution, titre='Offre dev Django',
            description='...', type_offre='intra',
        )
        Offre.objects.create(
            institution_id=self.institution, titre='Offre design UX',
            description='...', type_offre='inter',
        )

    def test_filtre_par_type(self):
        response = self.client.get(reverse('offre:offres_list'), {'type': 'intra'})
        titres = [o.titre for o in response.context['offres']]
        self.assertIn('Offre dev Django', titres)
        self.assertNotIn('Offre design UX', titres)

    def test_recherche_par_titre(self):
        response = self.client.get(reverse('offre:offres_list'), {'q': 'Django'})
        titres = [o.titre for o in response.context['offres']]
        self.assertEqual(titres, ['Offre dev Django'])