from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.utils.timesince import timesince

from .models import Offre
from account.models import Institution
from .forms import OffreForm
from core.models import Competence


from core.utils import paginate


# ==========================================================
# OFFRES
# ==========================================================
# Ajouter une offre
@login_required
def ajouter_offre(request):
    if request.user.role not in ['institution', 'admin']:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = OffreForm(request.POST)

        if form.is_valid():
            offre = form.save(commit=False)

            # Institution
            if request.user.role == 'institution':

                institution = getattr(request.user, 'profil_institution', None)

                if not institution:
                    return redirect('core:dashboard')

                offre.institution_id = (institution)

            # Admin
            elif request.user.role == 'admin':
                institution = form.cleaned_data.get('institution')                

                if institution:
                    offre.institution_id = (institution)

            # IMPORTANT
            # on sauvegarde AVANT
            offre.save()

            # sécurité :
            # forcer le refresh
            offre.refresh_from_db()

            competences = request.POST.getlist('competences')
            
            competences = competences[:5]

            for competence in competences:
                # nouvelle compétence
                if str(competence).startswith('new_'):
                    nom = competence.replace('new_', '').strip()

                    comp, created = Competence.objects.get_or_create(nom=nom)
                    offre.competences.add(comp)
                # compétence existante
                else:
                    offre.competences.add(int(competence))
            return redirect('offre:offres_list')
    else:
        form = OffreForm()

    return render(request, 'offre/add_offre.html', {'form': form})


# Liste des offres
@login_required
def list_offres(request):
    offres = Offre.objects.all().order_by('-date_publication')

    # Filtre par type
    type_filtre = request.GET.get('type')

    if type_filtre in ['intra', 'inter', 'mission_longue']:
        offres = offres.filter(type_offre=type_filtre)

    # Recherche
    query = request.GET.get('q')

    if query:
        offres = offres.filter(
            Q(titre__icontains=query) |
            Q(institution_id__nom_organisation__icontains=query)
        )

    # Mes offres (institutions uniquement)
    mes_offres = request.GET.get('mes_offres')

    if mes_offres == '1':
        if request.user.role != 'institution':
            return redirect('core:dashboard')

        institution = getattr(request.user, 'profil_institution', None)

        if not institution:
            return redirect('core:dashboard')

        offres = offres.filter(institution_id=institution)

    # Filtre par institution (ex : lien "Voir les offres" depuis une fiche institution)
    institution_filtre = request.GET.get('institution')

    if institution_filtre:
        offres = offres.filter(institution_id=institution_filtre, statut='publiee')

    # Pagination (appliquée après tous les filtres)
    page_obj = paginate(request, offres, per_page=30)

    # Temps écoulé (calculé seulement sur les offres de la page courante)
    for offre in page_obj:

        if offre.date_publication:
            temps_brut = timesince(offre.date_publication)
            offre.temps_ecoule = (temps_brut.split(',')[0])

            if offre.temps_ecoule == "0 minute":
                offre.temps_ecoule = ("À l'instant")

        else:
            offre.temps_ecoule = ("quelques instants")
            

    context = {
        'offres': page_obj,
        'page_obj': page_obj,
        'mes_offres': mes_offres,
        'type_filtre': type_filtre,
        'query': query,
    }

    return render(request,'offre/list_offres.html',context)


# Supprimer une offre
@login_required
def supprimer_offre(request, offre_id):
    # ADMIN → peut supprimer n'importe quelle offre
    if request.user.role == 'admin':
        offre = get_object_or_404(Offre,id=offre_id)

    # INSTITUTION → seulement ses offres
    elif request.user.role == 'institution':
        institution = getattr(request.user,'profil_institution',None)

        if not institution:
            return redirect('core:dashboard')

        offre = get_object_or_404(Offre, institution_id=institution)

    else:
        return redirect('core:dashboard')

    if request.method == 'POST':
        offre.delete()
        return redirect('offre:offres_list')

    return render(request, 'offre/delete_offre.html',{'offre': offre})


# Modifier une offre
@login_required
def edit_offre(request, offre_id):

    # Vérification rôle
    if request.user.role not in ['institution','admin']:
        return redirect('core:dashboard')

    # Cas admin
    if request.user.role == 'admin':
        offre = get_object_or_404(Offre, id=offre_id)

    # Cas institution
    else:
        institution = getattr( request.user, 'profil_institution', None)

        if not institution:
            return redirect('core:dashboard')

        offre = get_object_or_404(Offre, id=offre_id, institution_id=institution)

    # POST
    if request.method == 'POST':
        form = OffreForm(request.POST, instance=offre)

        # Protection backend
        # Si admin + institution déjà existante
        if (request.user.role == 'admin'and offre.institution_id):
            form.fields['institution'].disabled = True

        if form.is_valid():
            offre = form.save(commit=False)

            # Institution connectée
            if (request.user.role== 'institution'):
                offre.institution_id = (institution)

            # Admin
            elif (request.user.role == 'admin'):
                # seulement si aucune institution
                if not offre.institution_id:
                    institution_admin = (form.cleaned_data.get('institution'))

                    if institution_admin:
                        offre.institution_id = (institution_admin)

            offre.save()
            form.save_m2m()

            return redirect('offre:offres_list')

    # GET
    else:
        form = OffreForm(instance=offre)

        # Champ readonly si déjà lié
        if (request.user.role == 'admin' and offre.institution_id):
            form.fields['institution'].disabled = True

    return render(request, 'offre/edit_offre.html',{'form': form,'offre': offre})






# ==========================================================
# RECHERCHE INSTITUTION (autocomplete, admin - champ Institution)
# ==========================================================
def search_institution(request):
 
    q = request.GET.get('q', '').strip()
    institutions = Institution.objects.filter(nom_organisation__icontains=q)[:10]
 
    results = []
 
    for institution in institutions:
        results.append({
            'id': institution.pk,
            'nom': institution.nom_organisation
        })
 
    return JsonResponse(results, safe=False)
 