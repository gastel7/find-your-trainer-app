from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Count, Max, Min
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from candidature.models import Candidature
from formation.models import Formation, InscriptionFormation
from core.utils import paginate
from account.models import User

from .models import Evaluation



# ==========================================
# EVALUATIONS RECUES
# ==========================================

@login_required
def evaluations_list(request):

    # Un admin n'est jamais lui-même évalué (il n'a ni offres, ni
    # formations) — "mes évaluations reçues" serait donc toujours vide
    # et inutile pour lui. On lui montre à la place un annuaire de tous
    # les utilisateurs de la plateforme ayant reçu au moins un avis.
    if request.user.role == 'admin':
        return _evaluations_list_admin(request)

    evaluations_base = (
        Evaluation.objects
        .filter(
            cible=request.user
        )
        .select_related(
            'auteur'
        )
        .order_by(
            '-date_evaluation'
        )
    )

    stats = evaluations_base.aggregate(
        moyenne=Avg(
            'note_evaluation'
        ),
        total=Count(
            'id'
        )
    )

    # Toutes les notes (non paginées, non filtrées par tri) : nécessaires
    # pour le graphique de répartition côté JS, qui doit refléter
    # l'ensemble des avis, peu importe le filtre "meilleure/pire" choisi.
    all_notes = list(evaluations_base.values_list('note_evaluation', flat=True))

    # ── Filtre "meilleure note reçue" / "moins bonne note reçue" ─────
    # Même vue pour formateurs et institutions (cible=request.user dans
    # les deux cas) : un formateur verra ainsi l'institution qui lui a
    # donné sa meilleure/pire note, une institution verra le formateur
    # correspondant — sans code séparé pour chaque rôle.
    tri = request.GET.get('tri', '')
    evaluations = evaluations_base

    if tri == 'meilleure':
        meilleure_note = evaluations_base.aggregate(m=Max('note_evaluation'))['m']
        if meilleure_note is not None:
            evaluations = evaluations_base.filter(note_evaluation=meilleure_note)
    elif tri == 'pire':
        pire_note = evaluations_base.aggregate(m=Min('note_evaluation'))['m']
        if pire_note is not None:
            evaluations = evaluations_base.filter(note_evaluation=pire_note)

    page_obj = paginate(request, evaluations, per_page=30)

    context = {
        'evaluations': page_obj,
        'page_obj': page_obj,
        'all_notes': all_notes,
        'tri': tri,

        'note_globale':
            round(
                stats['moyenne'],
                1
            ) if stats['moyenne']
            else 0,

        'nb_evaluations':
            stats['total']
    }

    return render(
        request,
        'evaluations/evaluations_list.html',
        context
    )


def _evaluations_list_admin(request):
    users_qs = (
        User.objects
        .filter(role__in=['formateur', 'institution'])
        .annotate(
            moyenne=Avg('evaluations_recues__note_evaluation'),
            total=Count('evaluations_recues')
        )
    )

    note_filter = request.GET.get('note', '')

    if note_filter == 'non_note':
        users_qs = users_qs.filter(total=0)
    elif note_filter == '1-2':
        users_qs = users_qs.filter(moyenne__gte=1, moyenne__lt=2)
    elif note_filter == '2-3':
        users_qs = users_qs.filter(moyenne__gte=2, moyenne__lt=3)
    elif note_filter == '3-4':
        users_qs = users_qs.filter(moyenne__gte=3, moyenne__lt=4)
    elif note_filter == '4-5':
        users_qs = users_qs.filter(moyenne__gte=4, moyenne__lte=5)

    users_qs = users_qs.order_by('-moyenne', '-total')

    total_utilisateurs_evalues = users_qs.count()
    page_obj = paginate(request, users_qs, per_page=30)

    # NB : User a déjà une @property 'note_globale' (lecture seule, sans
    # setter) — on utilise donc des noms différents ici pour ne pas
    # entrer en conflit avec elle.
    utilisateurs_evalues = list(page_obj)
    for u in utilisateurs_evalues:
        u.note_moyenne = round(u.moyenne, 1) if u.moyenne else 0
        u.nombre_avis = u.total

    context = {
        'utilisateurs_evalues': utilisateurs_evalues,
        'page_obj': page_obj,
        'total_utilisateurs_evalues': total_utilisateurs_evalues,
        'note_filter': note_filter,
    }

    return render(request, 'evaluations/evaluations_list_admin.html', context)


# ==========================================
# MES EVALUATIONS DONNEES
# ==========================================

@login_required
def mes_evaluations(request):

    evaluations = (
        Evaluation.objects
        .filter(
            auteur=request.user
        )
        .select_related(
            'cible'
        )
        .order_by(
            '-date_evaluation'
        )
    )

    return render(
        request,
        'evaluations/mes_evaluations.html',
        {
            'evaluations': evaluations
        }
    )


# ==========================================
# DETAIL EVALUATION
# ==========================================

@login_required
def detail_evaluation(
    request,
    evaluation_id
):

    evaluation = get_object_or_404(
        Evaluation,
        id=evaluation_id
    )

    return render(
        request,
        'evaluations/detail_evaluation.html',
        {
            'evaluation': evaluation
        }
    )



# ==========================================
# Est AJAX views
# ==========================================
def _est_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'

# ==========================================
# EVALUER CANDIDATURE
# ==========================================

@login_required
@require_POST
def evaluer_candidature(request, candidature_id):

    candidature = get_object_or_404(Candidature, id=candidature_id)

    # ── Vérifications ────────────────────────────────────────────
    if candidature.statut not in ['acceptee', 'refusee', 'retiree']:
        if _est_ajax(request):
            return JsonResponse({'ok': False, 'error': "Candidature non évaluable."}, status=400)
        messages.error(request, "Cette candidature ne peut pas encore être évaluée.")
        return redirect('candidature:candidatures_recues')

    cible = None

    if request.user.role == 'formateur':
        if candidature.formateur.user != request.user:
            if _est_ajax(request):
                return JsonResponse({'ok': False, 'error': "Interdit."}, status=403)
            return redirect('core:dashboard')
        cible = candidature.offre.institution_id.user

    elif request.user.role == 'institution':
        if candidature.offre.institution_id.user != request.user:
            if _est_ajax(request):
                return JsonResponse({'ok': False, 'error': "Interdit."}, status=403)
            return redirect('core:dashboard')
        cible = candidature.formateur.user

    elif request.user.role == 'admin':
        cible = candidature.formateur.user
    else:
        if _est_ajax(request):
            return JsonResponse({'ok': False, 'error': "Interdit."}, status=403)
        return redirect('core:dashboard')

    # ── Note obligatoire ─────────────────────────────────────────
    note = request.POST.get('note', '').strip()
    if not note or not note.isdigit() or not (1 <= int(note) <= 5):
        if _est_ajax(request):
            return JsonResponse({'ok': False, 'error': "Note invalide."}, status=400)
        messages.error(request, "Note invalide.")
        return redirect('candidature:candidatures_recues')

    commentaire = request.POST.get('commentaire', '').strip()

    # ── Sauvegarde ───────────────────────────────────────────────
    Evaluation.objects.update_or_create(
        auteur=request.user,
        cible=cible,
        offre=candidature.offre,
        defaults={
            'type_evaluation': 'candidature',
            'note_evaluation': int(note),
            'commentaire': commentaire
        }
    )

    if _est_ajax(request):
        return JsonResponse({'ok': True, 'message': "Évaluation enregistrée avec succès."})

    messages.success(request, "Évaluation enregistrée avec succès.")
    return redirect('evaluation:mes_evaluations')





# ==========================================
# EVALUER FORMATION
# ==========================================

@login_required
@require_POST
def evaluer_formation(request, formation_id):

    formation = get_object_or_404(Formation, id=formation_id)

    if not formation.est_terminee:
        if _est_ajax(request):
            return JsonResponse({'ok': False, 'error': "Formation non terminée."}, status=400)
        messages.error(request, "Cette formation n'est pas encore terminée.")
        return redirect('formation:formations_list')

    cible = None

    inscription = InscriptionFormation.objects.filter(
        formation=formation, participant=request.user
    ).first()

    # ── Participant évalue formateur ou co-intervenant ────────────
    if inscription:
        cible_id = request.POST.get('cible') or request.GET.get('cible')

        if cible_id:
            co = get_object_or_404(
                formation.co_intervenants.select_related('user'),
                user_id=cible_id
            )
            cible = co.user
        else:
            cible = formation.formateur.user

    # ── Formateur / co-intervenant évalue un participant ─────────
    elif hasattr(request.user, 'profil_formateur') and (
        formation.formateur.user == request.user or
        formation.co_intervenants.filter(user=request.user).exists()
    ):
        participant_id = request.POST.get('participant') or request.GET.get('participant')
        if not participant_id:
            if _est_ajax(request):
                return JsonResponse({'ok': False, 'error': "Participant introuvable."}, status=400)
            messages.error(request, "Participant introuvable.")
            return redirect('formation:formations_list')

        cible = get_object_or_404(User, id=participant_id)

        if not InscriptionFormation.objects.filter(
            formation=formation, participant=cible
        ).exists():
            if _est_ajax(request):
                return JsonResponse({'ok': False, 'error': "Participant non inscrit."}, status=400)
            messages.error(request, "Ce participant n'est pas inscrit à cette formation.")
            return redirect('formation:formations_list')
    else:
        if _est_ajax(request):
            return JsonResponse({'ok': False, 'error': "Interdit."}, status=403)
        return redirect('core:dashboard')

    # ── Note obligatoire ─────────────────────────────────────────
    note = request.POST.get('note', '').strip()
    if not note or not note.isdigit() or not (1 <= int(note) <= 5):
        if _est_ajax(request):
            return JsonResponse({'ok': False, 'error': "Note invalide."}, status=400)
        messages.error(request, "Note invalide.")
        return redirect('formation:formations_list')

    commentaire = request.POST.get('commentaire', '').strip()

    # ── Sauvegarde ───────────────────────────────────────────────
    Evaluation.objects.update_or_create(
        auteur=request.user,
        cible=cible,
        formation=formation,
        defaults={
            'type_evaluation': 'formation',
            'note_evaluation': int(note),
            'commentaire': commentaire
        }
    )

    if _est_ajax(request):
        return JsonResponse({'ok': True, 'message': "Évaluation enregistrée."})

    messages.success(request, "Évaluation enregistrée.")
    return redirect('evaluation:mes_evaluations')