from django.test import TestCase
from django.urls import reverse

from account.models import User, Formateur, Institution
from core.models import Competence


class IndexPageTestCase(TestCase):

    def test_page_accueil_accessible(self):
        response = self.client.get(reverse('core:index'))
        self.assertEqual(response.status_code, 200)


class DashboardTestCase(TestCase):
    """Le dashboard doit être accessible à chaque rôle, mais pas aux anonymes."""

    def test_anonyme_redirige_vers_login(self):
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_formateur(self):
        user = User.objects.create_user(username='form', password='x', role='formateur')
        Formateur.objects.create(user=user)
        self.client.force_login(user)

        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['role_actif'], 'formateur')

    def test_dashboard_institution(self):
        user = User.objects.create_user(username='inst', password='x', role='institution')
        Institution.objects.create(user=user, nom_organisation='Zepeck')
        self.client.force_login(user)

        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['role_actif'], 'institution')

    def test_dashboard_admin(self):
        user = User.objects.create_superuser(username='boss', password='x', email='boss@test.com')
        self.client.force_login(user)

        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['role_actif'], 'admin')


class SearchCompetenceTestCase(TestCase):

    def setUp(self):
        Competence.objects.create(nom='Django')
        Competence.objects.create(nom='React')
        Competence.objects.create(nom='Docker')

        user = User.objects.create_user(username='form', password='x', role='formateur')
        Formateur.objects.create(user=user)
        self.client.force_login(user)

    def test_recherche_partielle_insensible_a_la_casse(self):
        response = self.client.get(reverse('core:search_competence'), {'q': 'dja'})
        noms = [c['nom'] for c in response.json()]
        self.assertEqual(noms, ['Django'])

    def test_recherche_vide_ne_renvoie_rien(self):
        response = self.client.get(reverse('core:search_competence'), {'q': ''})
        self.assertEqual(response.json(), [])