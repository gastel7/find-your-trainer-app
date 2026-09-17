from django.test import TestCase
from django.urls import reverse

from account.models import User, Formateur, Institution
from offre.models import Offre
from candidature.models import Candidature
from notifications.models import Notification


class PostulerOffreTestCase(TestCase):

    def setUp(self):
        user_inst = User.objects.create_user(username='inst', password='x', role='institution')
        self.institution = Institution.objects.create(user=user_inst, nom_organisation='Zepeck')

        user_form = User.objects.create_user(username='form', password='x', role='formateur')
        self.formateur = Formateur.objects.create(user=user_form)

        self.offre = Offre.objects.create(
            institution_id=self.institution, titre='Mission Django',
            description='...', type_offre='intra', nb_max_de_candidatures=1,
        )

        self.client.force_login(user_form)

    def test_postuler_cree_la_candidature(self):
        self.client.post(reverse('candidature:postuler_offre', args=[self.offre.id]), {'message': 'Motivé !'})
        self.assertTrue(Candidature.objects.filter(offre=self.offre, formateur=self.formateur).exists())

    def test_double_candidature_refusee(self):
        Candidature.objects.create(offre=self.offre, formateur=self.formateur)
        self.client.post(reverse('candidature:postuler_offre', args=[self.offre.id]))
        self.assertEqual(Candidature.objects.filter(offre=self.offre, formateur=self.formateur).count(), 1)

    def test_quota_max_atteint(self):
        Candidature.objects.create(offre=self.offre, formateur=self.formateur)

        autre_user = User.objects.create_user(username='form2', password='x', role='formateur')
        autre_formateur = Formateur.objects.create(user=autre_user)
        client2 = self.client_class()
        client2.force_login(autre_user)

        client2.post(reverse('candidature:postuler_offre', args=[self.offre.id]))
        self.assertFalse(Candidature.objects.filter(offre=self.offre, formateur=autre_formateur).exists())


class DecisionCandidatureTestCase(TestCase):
    """Acceptation/refus + la notification qui doit en découler."""

    def setUp(self):
        user_inst = User.objects.create_user(username='inst', password='x', role='institution')
        self.institution = Institution.objects.create(user=user_inst, nom_organisation='Zepeck')

        user_form = User.objects.create_user(username='form', password='x', role='formateur')
        self.formateur_user = user_form
        self.formateur = Formateur.objects.create(user=user_form)

        self.offre = Offre.objects.create(
            institution_id=self.institution, titre='Mission Django',
            description='...', type_offre='intra',
        )
        self.candidature = Candidature.objects.create(offre=self.offre, formateur=self.formateur)

        self.client.force_login(user_inst)

    def test_acceptation_change_le_statut(self):
        self.client.post(reverse('candidature:accepter_candidature', args=[self.candidature.id]))
        self.candidature.refresh_from_db()
        self.assertEqual(self.candidature.statut, 'acceptee')

    def test_acceptation_notifie_le_formateur(self):
        self.client.post(reverse('candidature:accepter_candidature', args=[self.candidature.id]))
        self.assertTrue(Notification.objects.filter(user=self.formateur_user).exists())

    def test_refus_change_le_statut(self):
        self.client.post(reverse('candidature:refuser_candidature', args=[self.candidature.id]))
        self.candidature.refresh_from_db()
        self.assertEqual(self.candidature.statut, 'refusee')

    def test_refus_notifie_le_formateur(self):
        self.client.post(reverse('candidature:refuser_candidature', args=[self.candidature.id]))
        self.assertTrue(Notification.objects.filter(user=self.formateur_user).exists())


class RecherchesListesCandidaturesTestCase(TestCase):
    """La barre de recherche ajoutée sur mes_candidatures / candidatures_recues."""

    def setUp(self):
        user_inst = User.objects.create_user(username='inst', password='x', role='institution')
        self.institution = Institution.objects.create(user=user_inst, nom_organisation='Zepeck Services')

        user_form = User.objects.create_user(username='form', password='x', role='formateur')
        self.formateur = Formateur.objects.create(user=user_form)

        self.offre = Offre.objects.create(
            institution_id=self.institution, titre='Mission React',
            description='...', type_offre='intra',
        )
        Candidature.objects.create(offre=self.offre, formateur=self.formateur)

        self.client_formateur = self.client_class()
        self.client_formateur.force_login(user_form)

        self.client_institution = self.client_class()
        self.client_institution.force_login(user_inst)

    def test_mes_candidatures_recherche_par_titre_offre(self):
        response = self.client_formateur.get(reverse('candidature:mes_candidatures'), {'q': 'React'})
        self.assertEqual(len(response.context['candidatures']), 1)

    def test_mes_candidatures_recherche_sans_resultat(self):
        response = self.client_formateur.get(reverse('candidature:mes_candidatures'), {'q': 'Introuvable'})
        self.assertEqual(len(response.context['candidatures']), 0)

    def test_candidatures_recues_recherche_par_formateur(self):
        response = self.client_institution.get(reverse('candidature:candidatures_recues'), {'q': 'form'})
        self.assertEqual(len(response.context['candidatures']), 1)