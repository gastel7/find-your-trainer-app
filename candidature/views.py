from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Avg, Count as DbCount, Q
from django.utils import timezone
from django.urls import reverse
import csv


from offre.models import Offre
from account.models import Formateur, Institution,User
from .models import Candidature
from evaluation.models import Evaluation
from notifications.services import notifier_utilisateur

# Create your views here.
# ==========================
# CANDIDATURES
# ==========================

@login_required
def postuler_offre(request, offre_id):

    if request.method != "POST":
        return redirect('offre:offres_list')

    offre = get_object_or_404(
        Offre,
        id=offre_id
    )

    if request.user.role not in ['formateur', 'admin']:
        return redirect('core:dashboard')

    # Vérification quota
    if offre.candidatures.count() >= offre.nb_max_de_candidatures:
        messages.error(
            request,
            "Le nombre maximum de candidatures a été atteint."
        )

        return redirect('offre:offres_list')

    # =====================
    # FORMATEUR
    # =====================

    if request.user.role == 'formateur':

        formateur = getattr(
            request.user,
            'profil_formateur',
            None
        )

        if not formateur:
            messages.error(
                request,
                "Profil formateur introuvable."
            )

            return redirect('offre:offres_list')

    # =====================
    # ADMIN
    # =====================

    else:

        formateur_id = request.POST.get(
            'formateur'
        )

        if not formateur_id:

            messages.error(
                request,
                "Veuillez sélectionner un formateur."
            )

            return redirect(
                'offre:offres_list'
            )

        formateur = get_object_or_404(
            Formateur,
            pk=formateur_id
        )

    # =====================
    # Déjà candidat ?
    # =====================

    if Candidature.objects.filter(
        offre=offre,
        formateur=formateur
    ).exists():

        messages.warning(
            request,
            "Ce formateur a déjà postulé à cette offre."
        )

        return redirect(
            'offre:offres_list'
        )

    Candidature.objects.create(
        offre=offre,
        formateur=formateur,
        message=request.POST.get(
            'message',
            ''
        ),
        cv=request.FILES.get(
            'cv'
        )
    )

    messages.success(
        request,
        "Candidature envoyée avec succès."
    )

    return redirect(
        'candidature:mes_candidatures'
    )



def _annoter_eval_par_candidature(candidatures_list, auteur, cible_id_getter):
    """
    Enrichit chaque candidature avec 4 attributs utilisés dans le template :
      .eval_note          → note moyenne de la cible (float, 0 si aucune)
      .eval_count         → nombre d'évaluations reçues par la cible (int)
      .eval_commentaire   → commentaire laissé par auteur sur cette offre (str)
      .eval_note_existante→ note laissée par auteur sur cette offre (int, 0 si aucune)

    cible_id_getter : callable(candidature) → user_id de la cible
    """
    if not candidatures_list:
        return

    cible_ids = [cible_id_getter(c) for c in candidatures_list]
    offre_ids  = [c.offre_id for c in candidatures_list]

    # ── Stats globales de la cible (agrégées en 1 seule requête) ────
    stats_qs = (
        Evaluation.objects
        .filter(cible_id__in=cible_ids)
        .values('cible_id')
        .annotate(moyenne=Avg('note_evaluation'), total=DbCount('id'))
    )
    stats_dict = {row['cible_id']: row for row in stats_qs}

    # ── Évaluations déjà posées par cet auteur sur ces offres ───────
    existing_qs = (
        Evaluation.objects
        .filter(
            auteur=auteur,
            type_evaluation='candidature',
            offre_id__in=offre_ids
        )
        .values('offre_id', 'note_evaluation', 'commentaire')
    )
    existing_dict = {row['offre_id']: row for row in existing_qs}

    for c in candidatures_list:
        cible_id = cible_id_getter(c)
        stats    = stats_dict.get(cible_id, {})
        existing = existing_dict.get(c.offre_id, {})

        c.eval_note           = round(float(stats.get('moyenne') or 0), 1)
        c.eval_count          = stats.get('total', 0) or 0
        c.eval_commentaire    = existing.get('commentaire', '') or ''
        c.eval_note_existante = existing.get('note_evaluation', 0) or 0


@login_required
def mes_candidatures(request):

    if request.user.role not in ['formateur', 'admin']:
        return redirect('core:dashboard')

    candidatures = (
        Candidature.objects
        .select_related(
            'offre',
            'offre__institution_id',
            'offre__institution_id__user',
            'formateur',
            'formateur__user',
        )
    )

    # ── Formateur ─────────────────────────────────────────────────
    if request.user.role == 'formateur':
        formateur = getattr(request.user, 'profil_formateur', None)
        candidatures = candidatures.filter(formateur=formateur)

    # ── Filtre statut ─────────────────────────────────────────────
    statut = request.GET.get('statut')
    if statut:
        candidatures = candidatures.filter(statut=statut)

    # ── Recherche texte : nom de l'entreprise OU titre de l'offre ──
    q = request.GET.get('q', '').strip()
    if q:
        candidatures = candidatures.filter(
            Q(offre__institution_id__nom_organisation__icontains=q) |
            Q(offre__titre__icontains=q)
        )

    # ── Date de candidature ─────────────────────────────────────────
    date_candidature = request.GET.get('date_candidature', '').strip()
    if date_candidature:
        candidatures = candidatures.filter(date_candidature__date=date_candidature)

    # ── Date de réponse (uniquement si une réponse a été donnée) ────
    date_reponse = request.GET.get('date_reponse', '').strip()
    if date_reponse:
        candidatures = candidatures.filter(date_traitement__date=date_reponse)

    # ── Compteurs ─────────────────────────────────────────────────
    candidatures_base = Candidature.objects.select_related('offre')
    if request.user.role == 'formateur':
        candidatures_base = candidatures_base.filter(formateur=formateur)

    # ── Données d'évaluation par candidature ─────────────────────
    # Formateur évalue l'institution → cible = institution.user
    candidatures_list = list(candidatures)
    _annoter_eval_par_candidature(
        candidatures_list,
        auteur=request.user,
        cible_id_getter=lambda c: c.offre.institution_id.user_id
    )

    context = {
        'candidatures'      : candidatures_list,
        'current_filter'    : statut,
        'q'                 : q,
        'date_candidature'  : date_candidature,
        'date_reponse'      : date_reponse,
        'total_candidatures': candidatures_base.count(),
        'en_attente_count'  : candidatures_base.filter(statut='en_attente').count(),
        'acceptees_count'   : candidatures_base.filter(statut='acceptee').count(),
        'refusees_count'    : candidatures_base.filter(statut='refusee').count(),
        'retirees_count'    : candidatures_base.filter(statut='retiree').count(),
    }

    return render(request, 'candidatures/mes_candidatures.html', context)


@login_required
def candidatures_recues(request):

    if request.user.role not in ['institution', 'admin']:
        return redirect('core:dashboard')

    candidatures = (
        Candidature.objects
        .select_related(
            'offre',
            'offre__institution_id',
            'formateur',
            'formateur__user',
        )
    )

    # ── Institution ───────────────────────────────────────────────
    if request.user.role == 'institution':
        institution = getattr(request.user, 'profil_institution', None)
        candidatures = candidatures.filter(offre__institution_id=institution)

    # ── Filtre statut ─────────────────────────────────────────────
    statut = request.GET.get('statut')
    if statut:
        candidatures = candidatures.filter(statut=statut)

    # ── Recherche texte : username/prénom/nom du formateur OU titre offre ──
    q = request.GET.get('q', '').strip()
    if q:
        candidatures = candidatures.filter(
            Q(formateur__user__username__icontains=q) |
            Q(formateur__user__first_name__icontains=q) |
            Q(formateur__user__last_name__icontains=q) |
            Q(offre__titre__icontains=q)
        )

    # ── Date de candidature ─────────────────────────────────────────
    date_candidature = request.GET.get('date_candidature', '').strip()
    if date_candidature:
        candidatures = candidatures.filter(date_candidature__date=date_candidature)

    # ── Date de réponse (uniquement si l'institution a déjà répondu) ─
    date_reponse = request.GET.get('date_reponse', '').strip()
    if date_reponse:
        candidatures = candidatures.filter(date_traitement__date=date_reponse)

    # ── Compteurs ─────────────────────────────────────────────────
    candidatures_base = Candidature.objects.select_related('offre')
    if request.user.role == 'institution':
        candidatures_base = candidatures_base.filter(offre__institution_id=institution)

    # ── Données d'évaluation par candidature ─────────────────────
    # Institution évalue le formateur → cible = formateur.user
    candidatures_list = list(candidatures)
    _annoter_eval_par_candidature(
        candidatures_list,
        auteur=request.user,
        cible_id_getter=lambda c: c.formateur.user_id
    )

    context = {
        'candidatures'      : candidatures_list,
        'current_filter'    : statut,
        'q'                 : q,
        'date_candidature'  : date_candidature,
        'date_reponse'      : date_reponse,
        'total_candidatures': candidatures_base.count(),
        'en_attente_count'  : candidatures_base.filter(statut='en_attente').count(),
        'acceptees_count'   : candidatures_base.filter(statut='acceptee').count(),
        'refusees_count'    : candidatures_base.filter(statut='refusee').count(),
        'retirees_count'    : candidatures_base.filter(statut='retiree').count(),
    }

    return render(request, 'candidatures/candidatures_recues.html', context)


# Candidature - Actions (accepter)
@login_required
def accepter_candidature(
    request,
    candidature_id
):

    candidature = get_object_or_404(
        Candidature,
        id=candidature_id
    )

    # Action irréversible
    if candidature.statut != 'en_attente':

        messages.error(
            request,
            "Cette candidature a déjà été traitée."
        )

        return redirect(
            'candidature:candidatures_recues'
        )

    if request.user.role not in [
        'institution',
        'admin'
    ]:
        return redirect(
            'core:dashboard'
        )

    if request.user.role == 'institution':

        institution = getattr(
            request.user,
            'profil_institution',
            None
        )

        if candidature.offre.institution_id != institution:
            return redirect(
                'core:dashboard'
            )

    candidature.statut = 'acceptee'
    candidature.commentaire_decision = request.POST.get(
        'commentaire_decision',
        ''
    )
    candidature.date_traitement = timezone.now()
    candidature.traitee_par = request.user

    candidature.save()

    notifier_utilisateur(
        candidature.formateur.user,
        titre="Candidature acceptée 🎉",
        message=f"Ta candidature pour « {candidature.offre.titre} » a été acceptée.",
        url=reverse('candidature:mes_candidatures'),
    )

    messages.success(
        request,
        "Candidature acceptée."
    )

    return redirect(
        'candidature:candidatures_recues'
    )

# Candidature - Actions (refuser)
@login_required
def refuser_candidature(
    request,
    candidature_id
):

    candidature = get_object_or_404(
        Candidature,
        id=candidature_id
    )

    if candidature.statut != 'en_attente':

        messages.error(
            request,
            "Cette candidature a déjà été traitée."
        )

        return redirect(
            'candidature:candidatures_recues'
        )

    if request.user.role not in [
        'institution',
        'admin'
    ]:
        return redirect(
            'core:dashboard'
        )

    if request.user.role == 'institution':

        institution = getattr(
            request.user,
            'profil_institution',
            None
        )

        if candidature.offre.institution_id != institution:
            return redirect(
                'core:dashboard'
            )

    candidature.statut = 'refusee'
    candidature.commentaire_decision = request.POST.get(
        'commentaire_decision',
        ''
    )
    candidature.date_traitement = timezone.now()
    candidature.traitee_par = request.user

    candidature.save()

    notifier_utilisateur(
        candidature.formateur.user,
        titre="Candidature refusée",
        message=f"Ta candidature pour « {candidature.offre.titre} » n'a pas été retenue.",
        url=reverse('candidature:mes_candidatures'),
    )

    messages.success(
        request,
        "Candidature refusée."
    )

    return redirect(
        'candidature:candidatures_recues'
    )


# Candidature - Actions (retirer)
@login_required
def retirer_candidature(
    request,
    candidature_id
):

    candidature = get_object_or_404(
        Candidature,
        id=candidature_id
    )

    if candidature.statut != 'en_attente':

        messages.error(
            request,
            "Cette candidature a déjà été traitée."
        )

        return redirect(
            'candidature:mes_candidatures'
        )

    if request.user.role not in [
        'formateur',
        'admin'
    ]:
        return redirect(
            'core:dashboard'
        )

    if request.user.role == 'formateur':

        formateur = getattr(
            request.user,
            'profil_formateur',
            None
        )

        if candidature.formateur != formateur:
            return redirect(
                'core:dashboard'
            )

    candidature.statut = 'retiree'
    candidature.commentaire_decision = request.POST.get(
        'commentaire_decision',
        ''
    )
    candidature.date_traitement = timezone.now()
    candidature.traitee_par = request.user

    candidature.save()

    messages.success(
        request,
        "Candidature retirée."
    )

    return redirect(
        'candidature:mes_candidatures'
    )

def _get_candidatures_pour_export(request):
    """
    Reconstruit le même queryset que celui affiché à l'écran.
    Si `ids` est fourni (cas normal : le JS l'envoie avec les cartes
    actuellement visibles, donc la page en cours), on exporte EXACTEMENT
    ces candidatures-là — sinon on retombe sur les filtres classiques
    (recherche/statut/dates), par exemple si le lien est ouvert dans un
    nouvel onglet sans JS.
    """
    candidatures = Candidature.objects.select_related(
        'offre', 'offre__institution_id', 'formateur', 'formateur__user'
    )

    ids = request.GET.get('ids', '').strip()
    if ids:
        id_list = [i for i in ids.split(',') if i.isdigit()]
        return candidatures.filter(id__in=id_list).order_by('-date_candidature')

    statut = request.GET.get('statut')
    if statut:
        candidatures = candidatures.filter(statut=statut)

    q = request.GET.get('q', '').strip()
    if q:
        candidatures = candidatures.filter(
            Q(offre__institution_id__nom_organisation__icontains=q) |
            Q(offre__titre__icontains=q) |
            Q(formateur__user__username__icontains=q) |
            Q(formateur__user__first_name__icontains=q) |
            Q(formateur__user__last_name__icontains=q)
        )

    date_candidature = request.GET.get('date_candidature', '').strip()
    if date_candidature:
        candidatures = candidatures.filter(date_candidature__date=date_candidature)

    date_reponse = request.GET.get('date_reponse', '').strip()
    if date_reponse:
        candidatures = candidatures.filter(date_traitement__date=date_reponse)

    return candidatures.order_by('-date_candidature')


@login_required
def exporter_candidatures_csv(request):
    """Export CSV réservé à l'admin — cf. _get_candidatures_pour_export."""
    if request.user.role != 'admin':
        messages.error(request, "Accès réservé aux administrateurs.")
        return redirect('core:dashboard')

    candidatures = _get_candidatures_pour_export(request)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="candidatures_{timezone.now().strftime("%Y-%m-%d_%Hh%M")}.csv"'
    )
    # BOM UTF-8 pour qu'Excel affiche correctement les accents à l'ouverture
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Formateur', 'Entreprise', 'Offre', 'Statut',
        'Date de candidature', 'Date de réponse',
    ])

    for c in candidatures:
        writer.writerow([
            c.formateur.user.get_full_name() or c.formateur.user.username,
            c.offre.institution_id.nom_organisation,
            c.offre.titre,
            c.get_statut_display(),
            c.date_candidature.strftime('%d/%m/%Y %H:%M'),
            c.date_traitement.strftime('%d/%m/%Y %H:%M') if c.date_traitement else '',
        ])

    return response


@login_required
def exporter_candidatures_pdf(request):
    """Export PDF réservé à l'admin — même contenu/filtrage que le CSV."""
    if request.user.role != 'admin':
        messages.error(request, "Accès réservé aux administrateurs.")
        return redirect('core:dashboard')

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm

    candidatures = _get_candidatures_pour_export(request)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="candidatures_{timezone.now().strftime("%Y-%m-%d_%Hh%M")}.pdf"'
    )

    doc = SimpleDocTemplate(
        response, pagesize=landscape(A4),
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()

    elements = [
        Paragraph("Export des candidatures", styles['Title']),
        Paragraph(
            f"Généré le {timezone.now().strftime('%d/%m/%Y à %H:%M')} — {candidatures.count()} candidature(s)",
            styles['Normal'],
        ),
        Spacer(1, 0.6 * cm),
    ]

    data = [['Formateur', 'Entreprise', 'Offre', 'Statut', 'Date de candidature', 'Date de réponse']]
    for c in candidatures:
        data.append([
            c.formateur.user.get_full_name() or c.formateur.user.username,
            c.offre.institution_id.nom_organisation,
            c.offre.titre,
            c.get_statut_display(),
            c.date_candidature.strftime('%d/%m/%Y %H:%M'),
            c.date_traitement.strftime('%d/%m/%Y %H:%M') if c.date_traitement else '—',
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0b1535')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)

    doc.build(elements)
    return response