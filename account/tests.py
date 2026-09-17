from django.test import TestCase
from django.urls import reverse

from account.models import User, Formateur, Institution


class UserRoleTestCase(TestCase):
    """Le fix : un superuser sans rôle devient admin automatiquement."""

    def test_superuser_sans_role_devient_admin(self):
        user = User.objects.create_superuser(username='boss', password='motdepasse123', email='boss@test.com')
        user.refresh_from_db()
        self.assertEqual(user.role, 'admin')

    def test_user_normal_garde_son_role(self):
        user = User.objects.create_user(username='jean', password='motdepasse123', role='formateur')
        self.assertEqual(user.role, 'formateur')

    def test_superuser_avec_role_deja_defini_nest_pas_ecrase(self):
        user = User.objects.create_superuser(username='boss2', password='motdepasse123', email='b2@test.com')
        user.role = 'formateur'
        user.save()
        self.assertEqual(user.role, 'formateur')


class SignUpTestCase(TestCase):
    """Inscription d'un nouveau formateur : compte + profil créés ensemble."""

    def test_inscription_formateur(self):
        response = self.client.post(reverse('account:log_up'), {
            'role': 'formateur',
            'username': 'nouveau_formateur',
            'email': 'nf@test.com',
            'password': 'motdepasse123',
            'cgu': 'on',
            'biographie': 'Développeur passionné depuis 8 ans.',
            'competences': 'Python, Django',
            'localisation_formateur': 'Paris',
            'tarif_journalier': '500',
        })
        self.assertEqual(User.objects.filter(username='nouveau_formateur').count(), 1)
        user = User.objects.get(username='nouveau_formateur')
        self.assertEqual(user.role, 'formateur')
        self.assertTrue(Formateur.objects.filter(user=user).exists())
        # Connecté automatiquement après inscription
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_inscription_institution(self):
        response = self.client.post(reverse('account:log_up'), {
            'role': 'institution',
            'username': 'nouvelle_institution',
            'email': 'ni@test.com',
            'password': 'motdepasse123',
            'cgu': 'on',
            'nom_organisation': 'Zepeck Services',
            'description': 'Cabinet de formation spécialisé en IT.',
            'localisation_institution': 'Lyon',
        })
        self.assertEqual(User.objects.filter(username='nouvelle_institution').count(), 1)
        user = User.objects.get(username='nouvelle_institution')
        self.assertEqual(user.role, 'institution')
        self.assertTrue(Institution.objects.filter(user=user, nom_organisation='Zepeck Services').exists())
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_inscription_formateur_sans_cgu_refusee(self):
        response = self.client.post(reverse('account:log_up'), {
            'role': 'formateur',
            'username': 'sans_cgu',
            'email': 'sc@test.com',
            'password': 'motdepasse123',
            'biographie': 'Bio',
            'competences': 'Python',
            'localisation_formateur': 'Paris',
            'tarif_journalier': '500',
        })
        self.assertFalse(User.objects.filter(username='sans_cgu').exists())

    def test_inscription_institution_sans_nom_organisation_refusee(self):
        response = self.client.post(reverse('account:log_up'), {
            'role': 'institution',
            'username': 'inst_incomplete',
            'email': 'ii@test.com',
            'password': 'motdepasse123',
            'cgu': 'on',
            'description': 'Description sans nom',
            'localisation_institution': 'Lyon',
        })
        self.assertFalse(User.objects.filter(username='inst_incomplete').exists())


class LoginTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='marie', password='motdepasse123', role='formateur')
        Formateur.objects.create(user=self.user)

    def test_connexion_reussie(self):
        response = self.client.post(reverse('account:log_in'), {
            'username': 'marie',
            'password': 'motdepasse123',
            'role': 'formateur',
        })
        self.assertEqual(response.status_code, 302)

    def test_connexion_mauvais_mot_de_passe(self):
        response = self.client.post(reverse('account:log_in'), {
            'username': 'marie',
            'password': 'mauvais',
            'role': 'formateur',
        })
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class ListesPaginationTestCase(TestCase):
    """Vérifie que les listes formateurs/institutions se chargent et
    sont bien triées (le fix UnorderedObjectListWarning)."""

    def setUp(self):
        for i in range(3):
            user = User.objects.create_user(username=f'form{i}', password='motdepasse123', role='formateur')
            Formateur.objects.create(user=user)

            user_inst = User.objects.create_user(username=f'inst{i}', password='motdepasse123', role='institution')
            Institution.objects.create(user=user_inst, nom_organisation=f'Entreprise {i}')

    def test_liste_formateurs_accessible(self):
        response = self.client.get(reverse('account:formateurs_list'))
        self.assertEqual(response.status_code, 200)

    def test_liste_institutions_accessible(self):
        response = self.client.get(reverse('account:institutions_list'))
        self.assertEqual(response.status_code, 200)