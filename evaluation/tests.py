from django.test import TestCase
from django.urls import reverse
from django.db import IntegrityError
from django.core.exceptions import ValidationError

from account.models import User, Formateur, Institution
from offre.models import Offre
from candidature.models import Candidature
from evaluation.models import Evaluation


class EvaluationModelTestCase(TestCase):

    def setUp(self):
        self.auteur = User.objects.create_user(username='auteur', password='x', role='formateur')
        self.cible = User.objects.create_user(username='cible', password='x', role='institution')

        user_inst = User.objects.create_user(username='inst', password='x', role='institution')
        self.institution = Institution.objects.create(user=user_inst, nom_organisation='Zepeck')
        self.offre = Offre.objects.create(
            institution_id=self.institution, titre='Mission', description='...', type_offre='intra',
        )

    def test_clean_refuse_type_candidature_sans_offre(self):
        evaluation = Evaluation(
            auteur=self.auteur, cible=self.cible, type_evaluation='candidature',
            note_evaluation=5,
        )
        with self.assertRaises(ValidationError):
            evaluation.clean()

    def test_clean_accepte_type_candidature_avec_offre(self):
        evaluation = Evaluation(
            auteur=self.auteur, cible=self.cible, type_evaluation='candidature',
            note_evaluation=5, offre=self.offre,
        )
        evaluation.clean()  # ne doit pas lever d'exception

    def test_double_evaluation_meme_offre_refusee(self):
        Evaluation.objects.create(
            auteur=self.auteur, cible=self.cible, type_evaluation='candidature',
            note_evaluation=5, offre=self.offre,
        )
        with self.assertRaises(IntegrityError):
            Evaluation.objects.create(
                auteur=self.auteur, cible=self.cible, type_evaluation='candidature',
                note_evaluation=3, offre=self.offre,
            )


class EvaluerCandidatureViewTestCase(TestCase):

    def setUp(self):
        user_inst = User.objects.create_user(username='inst', password='x', role='institution')
        self.institution = Institution.objects.create(user=user_inst, nom_organisation='Zepeck')

        user_form = User.objects.create_user(username='form', password='x', role='formateur')
        self.formateur = Formateur.objects.create(user=user_form)
        self.formateur_user = user_form

        self.offre = Offre.objects.create(
            institution_id=self.institution, titre='Mission', description='...', type_offre='intra',
        )
        self.candidature = Candidature.objects.create(offre=self.offre, formateur=self.formateur, statut='acceptee')

        self.client.force_login(user_form)

    def test_note_valide_cree_levaluation(self):
        self.client.post(reverse('evaluation:evaluer_candidature', args=[self.candidature.id]), {
            'note': '5', 'commentaire': 'Très pro',
        })
        self.assertTrue(Evaluation.objects.filter(auteur=self.formateur_user, offre=self.offre).exists())

    def test_note_invalide_refusee(self):
        self.client.post(reverse('evaluation:evaluer_candidature', args=[self.candidature.id]), {'note': '9'})
        self.assertFalse(Evaluation.objects.filter(auteur=self.formateur_user, offre=self.offre).exists())

    def test_candidature_en_attente_non_evaluable(self):
        self.candidature.statut = 'en_attente'
        self.candidature.save()
        self.client.post(reverse('evaluation:evaluer_candidature', args=[self.candidature.id]), {'note': '5'})
        self.assertFalse(Evaluation.objects.filter(auteur=self.formateur_user, offre=self.offre).exists())