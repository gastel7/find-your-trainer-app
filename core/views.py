from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg, Count
from django.http import JsonResponse
from django.utils import timezone

from datetime import timedelta

from .models import Competence
from offre.models import Offre
from formation.models import Formation
from evaluation.models import Evaluation
from account.models import Formateur, Institution
from candidature.models import Candidature
from chat.models import Message as ChatMessage


# ---------------------------
# INDEX
# ---------------------------
def index(request):
    print(request.user)

    return render(request, 'core/index_page/index.html')


# ---------------------------
# DASHBOARD
# ---------------------------
@login_required
def dashboard(request):
    user = request.user
    context = {'user': user}
 
    # ── VUE FORMATEUR ────────────────────────────────────────────────
    if user.role == 'formateur':
        profil = getattr(user, 'profil_formateur', None)
 
        # Candidatures du formateur (5 dernières)
        candidatures = []
        if profil:
            candidatures = (
                Candidature.objects
                .filter(formateur=profil)
                .select_related('offre', 'offre__institution_id__user')
                .order_by('-date_candidature')[:5]
            )
 
        # Formations publiées (5 dernières)
        formations = (
            Formation.objects
            .filter(formateur=profil)
            .order_by('-date_creation')[:5]
            if profil else []
        )
 
        # Prochaine mission : candidature acceptée avec date_debut la plus proche
        prochaine_mission = (
            Candidature.objects
            .filter(formateur=profil, statut='acceptee', offre__date_debut__gte=timezone.now().date())
            .select_related('offre')
            .order_by('offre__date_debut')
            .first()
            if profil else None
        )
 
        jours_avant_mission = None
        if prochaine_mission and prochaine_mission.offre.date_debut:
            delta = prochaine_mission.offre.date_debut - timezone.now().date()
            jours_avant_mission = delta.days
 
        # Messages non lus
        messages_non_lus = ChatMessage.objects.filter(
            destinataire_id=user,
            is_read=False,
            is_delete=False
        ).count()
 
        # Dernières conversations (3 derniers expéditeurs différents)
        dernieres_conversations = (
            ChatMessage.objects
            .filter(destinataire_id=user, is_delete=False)
            .select_related('expediteur_id')
            .order_by('-date_envoi')
        )
        # On déduplique les expéditeurs côté Python (simple et efficace pour 3 résultats)
        vus = set()
        conversations_uniques = []
        for msg in dernieres_conversations:
            exp_id = msg.expediteur_id_id
            if exp_id not in vus:
                vus.add(exp_id)
                conversations_uniques.append(msg)
            if len(conversations_uniques) >= 3:
                break
 
        # Note moyenne reçue
        note_data = user.evaluations_recues.aggregate(
            moyenne=Avg('note_evaluation'),
            total=Count('id')
        )
        note_moyenne = round(note_data['moyenne'], 1) if note_data['moyenne'] else None
        nb_avis = note_data['total']
 
        context.update({
            'role_actif': 'formateur',
            'candidatures': candidatures,
            'nb_candidatures': Candidature.objects.filter(formateur=profil).count() if profil else 0,
            'formations': formations,
            'prochaine_mission': prochaine_mission,
            'jours_avant_mission': jours_avant_mission,
            'messages_non_lus': messages_non_lus,
            'conversations': conversations_uniques,
            'note_moyenne': note_moyenne,
            'nb_avis': nb_avis,
        })
 
    # ── VUE INSTITUTION ──────────────────────────────────────────────
    elif user.role == 'institution':
        profil = getattr(user, 'profil_institution', None)
 
        # Offres de l'institution (5 dernières publiées)
        offres = (
            Offre.objects
            .filter(institution_id=profil)
            .prefetch_related('candidatures')
            .order_by('-date_publication')[:5]
            if profil else []
        )
 
        # Candidatures reçues sur toutes ses offres
        nb_candidatures_recues = (
            Candidature.objects
            .filter(offre__institution_id=profil)
            .count()
            if profil else 0
        )
 
        # Missions actives (candidatures acceptées)
        nb_missions_actives = (
            Candidature.objects
            .filter(offre__institution_id=profil, statut='acceptee')
            .count()
            if profil else 0
        )
 
        # Messages non lus
        messages_non_lus = ChatMessage.objects.filter(
            destinataire_id=user,
            is_read=False,
            is_delete=False
        ).count()
 
        # Dernières conversations
        dernieres_conversations = (
            ChatMessage.objects
            .filter(destinataire_id=user, is_delete=False)
            .select_related('expediteur_id')
            .order_by('-date_envoi')
        )
        vus = set()
        conversations_uniques = []
        for msg in dernieres_conversations:
            exp_id = msg.expediteur_id_id
            if exp_id not in vus:
                vus.add(exp_id)
                conversations_uniques.append(msg)
            if len(conversations_uniques) >= 3:
                break
 
        context.update({
            'role_actif': 'institution',
            'offres': offres,
            'nb_offres': Offre.objects.filter(institution_id=profil).count() if profil else 0,
            'nb_candidatures_recues': nb_candidatures_recues,
            'nb_missions_actives': nb_missions_actives,
            'messages_non_lus': messages_non_lus,
            'conversations': conversations_uniques,
        })
 

    # ── VUE ADMIN ────────────────────────────────────────────────────
    else:
        debut_semaine = timezone.now() - timedelta(days=7)
 
        # ── Agrégats FORMATEURS ──────────────────────────────────────
        note_data = Evaluation.objects.aggregate(
            moyenne=Avg('note_evaluation'),
            total=Count('id')
        )
 
        admin_f = {
            # Totaux globaux
            'nb_formateurs':          Formateur.objects.count(),
            'nb_candidatures_total':  Candidature.objects.count(),
            'nb_formations_total':    Formation.objects.count(),
            'note_moyenne_globale':   round(note_data['moyenne'], 1) if note_data['moyenne'] else None,
            'nb_avis_total':          note_data['total'],
 
            # Deltas cette semaine
            'nouveaux_formateurs':    Formateur.objects.filter(user__date_inscription__gte=debut_semaine).count(),
            'candidatures_semaine':   Candidature.objects.filter(date_candidature__gte=debut_semaine).count(),
            'formations_semaine':     Formation.objects.filter(date_creation__gte=debut_semaine).count(),
        }
 
        # ── Agrégats INSTITUTIONS ────────────────────────────────────
        admin_i = {
            # Totaux globaux
            'nb_institutions':        Institution.objects.count(),
            'nb_offres_total':        Offre.objects.count(),
            'nb_missions_actives':    Candidature.objects.filter(statut='acceptee').count(),
            'nb_candidatures_recues': Candidature.objects.count(),
 
            # Deltas cette semaine
            'nouvelles_institutions': Institution.objects.filter(user__date_inscription__gte=debut_semaine).count(),
            'offres_semaine': Offre.objects.filter(date_publication__gte=debut_semaine).count(),
            'candidatures_semaine': Candidature.objects.filter(date_candidature__gte=debut_semaine).count(),
        }
 
        # ── Listes pour les cards ────────────────────────────────────
        derniers_formateurs = (
            Formateur.objects
            .select_related('user')
            .order_by('-user__date_inscription')[:5]
        )
 
        dernieres_candidatures = (
            Candidature.objects
            .filter(date_candidature__gte=debut_semaine)
            .select_related('offre', 'formateur__user')
            .order_by('-date_candidature')[:5]
        )
 
        dernieres_offres = (
            Offre.objects
            .select_related('institution_id')
            .prefetch_related('candidatures')
            .order_by('-date_publication')[:5]
        )
 
        # Institutions les plus actives cette semaine (nb d'offres publiées)
        institutions_actives = (
            Institution.objects
            .annotate(
                nb_offres_semaine=Count(
                    'offres',  # ← le bon related_name
                    filter=Q(offres__date_publication__gte=debut_semaine)
                )
            )
            .filter(nb_offres_semaine__gt=0)
            .order_by('-nb_offres_semaine')[:5]
        )
 
        context.update({
            'role_actif':             'admin',
            'admin_f':                admin_f,
            'admin_i':                admin_i,
            'derniers_formateurs':    derniers_formateurs,
            'dernieres_candidatures': dernieres_candidatures,
            'dernieres_offres':       dernieres_offres,
            'institutions_actives':   institutions_actives,
        })
 
    return render(request, 'core/app/dashboard.html', context)


# La recherche des compétences, autant du côté offre que du côté formation,
# se fait via une requête AJAX vers cette vue qui retourne les compétences au format JSON
@login_required
def search_competence(request):
    query = request.GET.get('q', '')
    competences = []

    if query:
        results = Competence.objects.filter(nom__icontains=query)[:10]

        competences = [
            {
                'id': competence.id,
                'nom': competence.nom
            }
            for competence in results
        ]

    return JsonResponse(competences, safe=False)
