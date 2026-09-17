from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.core.files.base import ContentFile

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from io import BytesIO
import re
import unicodedata

from .models import Formation, InscriptionFormation, Attestation
from .forms import FormationForm
from evaluation.models import Evaluation
from core.utils import paginate
from account.models import Formateur


# Ajouter formation
@login_required
def add_formation(request):
    # Vérification du rôle
    if request.user.role not in ['formateur', 'admin']:
        return redirect('core:dashboard')

    formateur = getattr(request.user, 'profil_formateur', None)

    # Un formateur doit posséder un profil formateur
    if request.user.role == 'formateur' and not formateur:
        return redirect('core:dashboard')

    if request.method == 'POST':

        form = FormationForm(request.POST)

        if form.is_valid():

            formation = form.save(commit=False)

            # Cas formateur
            if request.user.role == 'formateur':
                formation.formateur = formateur

            # Cas admin
            elif request.user.role == 'admin':
                formateur_selectionne = form.cleaned_data.get('formateur')

                if formateur_selectionne:
                    formation.formateur = formateur_selectionne

            formation.save()
            form.save_m2m()

            return redirect('formation:formations_list')
        else:
            print("=== ERREURS ADD FORMATION ===")
            print(form.errors)
    else:
        form = FormationForm()

    return render(request, 'formation/add_formation.html', {'form': form})



# Liste formations
def _annoter_eval_par_formation(formations_list, auteur):
    """
    Enrichit chaque formation avec 4 attributs utilisés dans le template
    pour le bouton "Évaluer" (évaluation du formateur principal) :
      .eval_note           → note moyenne reçue par le formateur (float, 0 si aucune)
      .eval_count          → nombre d'évaluations reçues par le formateur (int)
      .eval_commentaire    → commentaire déjà laissé par l'auteur sur cette formation (str)
      .eval_note_existante → note déjà laissée par l'auteur sur cette formation (int, 0 si aucune)
    """
    if not formations_list:
        return

    cible_ids = [f.formateur.user_id for f in formations_list]
    formation_ids = [f.id for f in formations_list]

    stats_qs = (
        Evaluation.objects
        .filter(cible_id__in=cible_ids, type_evaluation='formation')
        .values('cible_id')
        .annotate(moyenne=Avg('note_evaluation'), total=Count('id'))
    )
    stats_dict = {row['cible_id']: row for row in stats_qs}

    existing_qs = (
        Evaluation.objects
        .filter(
            auteur=auteur,
            type_evaluation='formation',
            formation_id__in=formation_ids
        )
        .values('formation_id', 'cible_id', 'note_evaluation', 'commentaire')
    )
    existing_dict = {(row['formation_id'], row['cible_id']): row for row in existing_qs}

    for f in formations_list:
        cible_id = f.formateur.user_id
        stats    = stats_dict.get(cible_id, {})
        existing = existing_dict.get((f.id, cible_id), {})

        f.eval_note           = round(float(stats.get('moyenne') or 0), 1)
        f.eval_count          = stats.get('total', 0) or 0
        f.eval_commentaire    = existing.get('commentaire', '') or ''
        f.eval_note_existante = existing.get('note_evaluation', 0) or 0


@login_required
def list_formations(request):

    formations = Formation.objects.all().select_related('formateur', 'formateur__user').order_by('-date_creation')
    

    # =====================
    # FILTRE CATEGORIE
    # =====================

    categorie = request.GET.get('categorie')

    if categorie:
        formations = formations.filter(categorie=categorie)

    # =====================
    # RECHERCHE
    # =====================

    query = request.GET.get('q')

    if query:
        formations = formations.filter(
            Q(titre__icontains=query) |
            Q(description__icontains=query)
        )

    # ── Pagination, puis données d'évaluation (formateur principal)
    #    calculées seulement pour les formations de la page courante ──
    page_obj = paginate(request, formations, per_page=12)
    formations_list = list(page_obj)
    _annoter_eval_par_formation(formations_list, auteur=request.user)

    context = {
        'formations': formations_list,
        'page_obj': page_obj,
        'categorie': categorie,
        'query': query,
    }

    return render(request, 'formation/list_formations.html', context)


# Modifier formation
@login_required
def edit_formation(request, formation_id):

    # Vérification rôle
    if request.user.role not in ['formateur', 'admin']:
        return redirect('core:dashboard')

    # Cas admin
    if request.user.role == 'admin':
        formation = get_object_or_404(Formation, id=formation_id)
        

    # Cas formateur
    else:
        formateur = getattr(request.user, 'profil_formateur', None)

        if not formateur:
            return redirect('core:dashboard')

        formation = get_object_or_404(Formation, id=formation_id, formateur=formateur)
        

    # POST
    if request.method == 'POST':
        form = FormationForm(request.POST, instance=formation)

        # Protection backend
        if request.user.role == 'admin' and formation.formateur:
            form.fields['formateur'].disabled = True

        if form.is_valid():
            formation = form.save(commit=False)
            print("FORM VALIDE")

            # Formateur connecté
            if request.user.role  == 'formateur':
                formation.formateur = formateur
                

            # Admin
            elif request.user.role == 'admin':
                # seulement si pas déjà lié
                if not formation.formateur:
                    formateur_admin = (form.cleaned_data.get('formateur'))

                    if formateur_admin:
                        formation.formateur = ( formateur_admin)

            formation.save()
            form.save_m2m()

            return redirect('formation:formations_list')
    # GET
    else:
        form = FormationForm(instance=formation)
        print(form.errors)

        # readonly
        if(request.user.role == 'admin' and formation.formateur):
            form.fields['formateur'].disabled = True

    return render(request, 'formation/edit_formation.html', {'form': form, 'formation': formation})


# Supprimer formation
@login_required
def delete_formation(request, formation_id):
    # ADMIN
    if request.user.role == 'admin':
        formation = get_object_or_404(Formation, id=formation_id)

    # FORMATEUR propriétaire
    elif request.user.role == 'formateur':
        formateur = getattr(request.user,'profil_formateur',None)

        if not formateur:
            return redirect('core:dashboard')

        formation = get_object_or_404(Formation, id=formation_id, formateur=formateur)

    else:
        return redirect('core:dashboard')

    if request.method == 'POST':
        formation.delete()
        return redirect('formation:formations_list')

    return render(request,'formation/delete_formation.html',{'formation': formation})


def _contexte_detail_formation(formation, user):
    """
    Construit le contexte complet pour la page/modale détail formation.
    Centralisé ici pour être réutilisé par detail_formation,
    inscription_formation et desinscription_formation (cas AJAX).
    """
 
    # ── L'auteur (formateur principal) ? ────────────────────────────
    est_auteur = (
        hasattr(user, 'profil_formateur') and
        formation.formateur.user == user
    )
 
    # ── Co-intervenant ? ─────────────────────────────────────────────
    est_co_intervenant = False
    profil_formateur = getattr(user, 'profil_formateur', None)
 
    if profil_formateur:
        est_co_intervenant = formation.co_intervenants.filter(
            pk=profil_formateur.pk
        ).exists()
 
    # ── Inscription existante ? ───────────────────────────────────────
    inscription = InscriptionFormation.objects.filter(
        formation=formation,
        participant=user
    ).first()
 
    # ── Peut s'inscrire ? ─────────────────────────────────────────────
    peut_s_inscrire = (
        not est_auteur
        and not est_co_intervenant
        and not inscription
        and not formation.est_complete
        and not formation.est_terminee
    )
 
    # ── Liste des participants (formateur, co-intervenants, admin) ────
    participants = None
 
    if est_auteur or est_co_intervenant or user.role == 'admin':
        participants = InscriptionFormation.objects.filter(
            formation=formation,
            statut='confirmee'
        ).select_related('participant').order_by('-date_inscription')
 
    return {
        'formation'          : formation,
        'est_auteur'         : est_auteur,
        'est_co_intervenant' : est_co_intervenant,
        'inscription'        : inscription,
        'peut_s_inscrire'    : peut_s_inscrire,
        'participants'       : participants,
    }
 
 
def _est_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'
 
 
@login_required
def detail_formation(request, formation_id):
    formation = get_object_or_404(Formation, id=formation_id)
    context = _contexte_detail_formation(formation, request.user)
 
    # ── AJAX → renvoie uniquement le fragment de la modale ───────────
    if _est_ajax(request):
        return render(request, 'formation/_detail_formation_modal.html', context)
 
    # ── Requête classique → page complète ─────────────────────────────
    return render(request, 'formation/detail_formation.html', context)
 
 
@login_required
@require_POST
def inscription_formation(request, formation_id):
 
    formation = get_object_or_404(Formation, id=formation_id)
    user = request.user
    is_ajax = _est_ajax(request)
 
    def refuser(message):
        messages.error(request, message)
        if is_ajax:
            context = _contexte_detail_formation(formation, user)
            return render(request, 'formation/_detail_formation_modal.html', context)
        
        return redirect('formation:detail_formation', formation_id=formation.id)
 
    # Auteur
    if formation.formateur.user == user:
        return refuser("Vous ne pouvez pas vous inscrire à votre propre formation.")
 
    # Co-intervenant
    profil_formateur = getattr(user, 'profil_formateur', None)
    if profil_formateur and formation.co_intervenants.filter(pk=profil_formateur.pk).exists():
        return refuser("Vous intervenez sur cette formation, vous ne pouvez pas vous y inscrire.")
 
    # Déjà inscrit
    if InscriptionFormation.objects.filter(formation=formation, participant=user).exists():
        return refuser("Vous êtes déjà inscrit à cette formation.")
 
    # Complète
    if formation.est_complete:
        return refuser("Cette formation est complète.")
 
    # Terminée
    if formation.est_terminee:
        return refuser("Cette formation est déjà terminée.")
 
    InscriptionFormation.objects.create(formation=formation, participant=user)
    messages.success(request, "Votre inscription a bien été enregistrée !")
 
    if is_ajax:
        context = _contexte_detail_formation(formation, user)
        return render(request, 'formation/_detail_formation_modal.html', context)
 
    return redirect('formation:detail_formation', formation_id=formation.id)
 
 
@login_required
@require_POST
def desinscription_formation(request, formation_id):
 
    formation = get_object_or_404(Formation, id=formation_id)
    is_ajax = _est_ajax(request)
 
    inscription = get_object_or_404(InscriptionFormation, formation=formation,participant=request.user)
    inscription.delete()
 
    messages.success(request, "Vous avez bien été désinscrit de cette formation.")
 
    if is_ajax:
        context = _contexte_detail_formation(formation, request.user)
        return render(request, 'formation/_detail_formation_modal.html', context)
 
    return redirect('formation:detail_formation', formation_id=formation.id)
 

# ═══════════════════════════════════════════════════════════════════
# Permissions partagées (auteur / co-intervenant / admin)
# ═══════════════════════════════════════════════════════════════════
 
def _est_responsable(formation, user):
    """Auteur, co-intervenant, ou admin : ceux qui gèrent la formation."""
    profil_formateur = getattr(user, 'profil_formateur', None)
 
    est_auteur = bool(profil_formateur) and formation.formateur_id == profil_formateur.pk
    est_co_intervenant = bool(profil_formateur) and formation.co_intervenants.filter(
        pk=profil_formateur.pk
    ).exists()
 
    return est_auteur or est_co_intervenant or user.role == 'admin'
 
 
# ═══════════════════════════════════════════════════════════════════
# Téléchargement du support PDF — réservé aux inscrits confirmés
# ═══════════════════════════════════════════════════════════════════
 
@login_required
def telecharger_support(request, formation_id):
 
    formation = get_object_or_404(Formation, id=formation_id)
 
    if not formation.support_pdf:
        raise Http404("Aucun support n'a été ajouté pour cette formation.")
 
    inscription = InscriptionFormation.objects.filter(
        formation=formation,
        participant=request.user,
        statut='confirmee'
    ).first()
 
    if not inscription:
        raise PermissionDenied(
            "Vous devez être inscrit à cette formation pour accéder au support."
        )
 
    return FileResponse(
        formation.support_pdf.open('rb'),
        as_attachment=True,
        filename=f"support_{formation.titre}.pdf"
    )
 
 
# ═══════════════════════════════════════════════════════════════════
# Marquer une formation comme terminée (override manuel)
# ═══════════════════════════════════════════════════════════════════
 
@login_required
@require_POST
def marquer_formation_terminee(request, formation_id):
 
    formation = get_object_or_404(Formation, id=formation_id)
 
    if not _est_responsable(formation, request.user):
        raise PermissionDenied(
            "Vous n'êtes pas autorisé à modifier le statut de cette formation."
        )
 
    formation.terminee_manuelle = True
    formation.save()
 
    messages.success(request, "La formation a été marquée comme terminée.")
 
    if _est_ajax(request):
        context = _contexte_detail_formation(formation, request.user)
        return render(
            request,
            'formation/_detail_formation_modal.html',
            context
        )
 
    return redirect('formation:detail_formation', formation_id=formation.id)
 
 
# ═══════════════════════════════════════════════════════════════════
# Génération de l'attestation PDF — réservée au(x) formateur(s)/admin
# ═══════════════════════════════════════════════════════════════════
 
@login_required
def generer_attestation(request, inscription_id):
 
    inscription = get_object_or_404(InscriptionFormation, id=inscription_id)
    formation = inscription.formation
 
    if not _est_responsable(formation, request.user):
        raise PermissionDenied(
            "Seul le formateur (ou un co-intervenant) peut générer l'attestation."
        )
 
    if not formation.est_terminee:
        messages.error(
            request,
            "Impossible de générer l'attestation : la formation n'est pas encore terminée."
        )
        return redirect('formation:detail_formation', formation_id=formation.id)
 
    if inscription.statut != 'confirmee':
        messages.error(request, "Cette inscription n'est pas confirmée.")
        return redirect('formation:detail_formation', formation_id=formation.id)
 
    # ── Réutilise l'attestation existante si elle a déjà été générée ──
    try:
        attestation = inscription.attestation
    except Attestation.DoesNotExist:
        attestation = None
 
    if attestation is None:
        pdf_buffer = _construire_attestation_pdf(inscription)
        nom_fichier = f"attestation_{inscription.participant.last_name}_{formation.id}.pdf"
 
        attestation = Attestation(inscription=inscription)
        attestation.fichier_pdf.save(
            nom_fichier,
            ContentFile(pdf_buffer.read()),
            save=True
        )
 
    return FileResponse(
        attestation.fichier_pdf.open('rb'),
        as_attachment=True,
        filename=attestation.fichier_pdf.name.split('/')[-1]
    )
 
 
def _construire_attestation_pdf(inscription):
    """Génère le PDF de l'attestation en mémoire (BytesIO) via reportlab."""
 
    formation = inscription.formation
    participant = inscription.participant
 
    buffer = BytesIO()
    largeur, hauteur = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
 
    # Bordures décoratives
    c.setStrokeColor(colors.HexColor("#4F46E5"))
    c.setLineWidth(3)
    c.rect(1.2 * cm, 1.2 * cm, largeur - 2.4 * cm, hauteur - 2.4 * cm)
 
    c.setStrokeColor(colors.HexColor("#A5B4FC"))
    c.setLineWidth(1)
    c.rect(1.6 * cm, 1.6 * cm, largeur - 3.2 * cm, hauteur - 3.2 * cm)
 
    # En-tête plateforme
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.HexColor("#4F46E5"))
    c.drawCentredString(largeur / 2, hauteur - 3 * cm, "FIND YOUR TRAINER")
 
    # Titre
    c.setFont("Helvetica-Bold", 28)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawCentredString(largeur / 2, hauteur - 4.5 * cm, "ATTESTATION DE FORMATION")
 
    # Intro
    c.setFont("Helvetica", 13)
    c.setFillColor(colors.HexColor("#374151"))
    c.drawCentredString(largeur / 2, hauteur - 6.5 * cm, "Nous certifions que")
 
    # Nom du participant
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(colors.HexColor("#4F46E5"))
    nom_complet = f"{participant.first_name} {participant.last_name}".strip() or participant.username
    c.drawCentredString(largeur / 2, hauteur - 7.6 * cm, nom_complet)
 
    # Formation suivie
    c.setFont("Helvetica", 13)
    c.setFillColor(colors.HexColor("#374151"))
    c.drawCentredString(largeur / 2, hauteur - 8.8 * cm, "a suivi avec succès la formation")
 
    c.setFont("Helvetica-Bold", 17)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawCentredString(largeur / 2, hauteur - 9.8 * cm, formation.titre)
 
    # Dates / durée
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#6B7280"))
 
    if formation.date_debut and formation.date_cloture:
        if formation.date_debut == formation.date_cloture:
            dates_txt = f"le {formation.date_debut.strftime('%d/%m/%Y')}"
        else:
            dates_txt = (
                f"du {formation.date_debut.strftime('%d/%m/%Y')} "
                f"au {formation.date_cloture.strftime('%d/%m/%Y')}"
            )
        duree_txt = f" — {formation.duree}"
    else:
        dates_txt, duree_txt = "", ""
 
    c.drawCentredString(largeur / 2, hauteur - 10.8 * cm, f"{dates_txt}{duree_txt}")
 
    # Formateur
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#374151"))
    nom_formateur = f"{formation.formateur.user.first_name} {formation.formateur.user.last_name}"
    c.drawString(3 * cm, 2.8 * cm, "Formateur :")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(3 * cm, 2.3 * cm, nom_formateur)
 
    # Référence + date de génération
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#9CA3AF"))
    reference = f"Réf. ATT-{formation.id:04d}-{inscription.id:04d}"
    c.drawRightString(largeur - 3 * cm, 2.3 * cm, reference)
    c.drawRightString(
        largeur - 3 * cm, 1.8 * cm,
        f"Généré le {timezone.now().strftime('%d/%m/%Y')}"
    )
 
    c.showPage()
    c.save()
    buffer.seek(0)
 
    return buffer
 

def _slugify_filename(texte):
    """Nettoie une chaîne pour un usage sûr dans un nom de fichier (sans accents/espaces)."""
    texte = unicodedata.normalize('NFKD', texte).encode('ascii', 'ignore').decode('ascii')
    texte = re.sub(r'[^\w\s-]', '', texte).strip()
    texte = re.sub(r'[\s]+', '_', texte)
    return texte
 
 

@login_required
def search_formateur(request):

    q = request.GET.get('q', '').strip()
    formateurs = Formateur.objects.select_related('user').filter(user__first_name__icontains=q)[:10]
    
    results = []

    for formateur in formateurs:

        full_name = (
            f"{formateur.user.first_name} "
            f"{formateur.user.last_name}"
        ).strip()

        results.append({
            'id': formateur.pk,
            'nom': full_name
        })

    return JsonResponse(results, safe=False)
