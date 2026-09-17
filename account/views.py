from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.urls import reverse
from account.forms import LoginForm
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.conf import settings
from account.models import Institution

from evaluation.models import Evaluation
from offre.models import Offre
from notifications.services import notifier_utilisateur

import json
import secrets
import urllib.request
import urllib.error
from urllib.parse import urlencode


from .forms import SignUpForm, LoginForm
from .models import User, Formateur, Institution
from .forms import ProfilUtilisateurForm, ProfilFormateurForm, ProfilInstitutionForm


User = get_user_model()

ITEMS_PAR_PAGE = 10  # ← 30 éléments par page, comme dans le reste du site


def _notifier_si_profil_incomplet(user):
    """Suggère de compléter prénom/nom si l'utilisateur n'a que son username
    (utile entre autres pour que son nom apparaisse correctement sur GestSup)."""
    if not user.first_name and not user.last_name:
        notifier_utilisateur(
            user,
            titre="Complète ton profil",
            message="Ajoute ton prénom et/ou ton nom dans les paramètres pour une meilleure expérience.",
            url=reverse('account:parametres_profil'),
        )

# La vue de connexion
# def log_in(request):
#     form = LoginForm()
#     if request.method == 'POST':
#         username = request.POST.get('username').lower()
#         password = request.POST.get('password')

#         user = authenticate(username=username, password=password)

#         if user is not None:
#             login(request, user)
#             return redirect('core:dashboard')
#         else:
#             print('no thing')
#             messages.error(request, "Nom d'utilisateur ou mot de passe incorrect")

#     return render(request, 'account/log/log_in.html', {'form': form})




def log_in(request):
    if request.user.is_authenticated:   
        return redirect("core:dashboard")

    form = LoginForm()
    if request.method == 'POST':
        username = request.POST.get('username').lower()
        password = request.POST.get('password')
        role_choisi = request.POST.get('role') # Récupéré via l'input hidden

        user = authenticate(username=username, password=password)

        print(role_choisi)

        if user is not None:
            # VERIFICATION : Est-ce que le rôle en DB correspond au choix du toggle ?
            if user.role == role_choisi:
                login(request, user)
                _notifier_si_profil_incomplet(user)

                # REDIRECTION CONDITIONNELLE
                if user.role == 'institution':
                    return redirect('core:dashboard')
                
                if user.role == 'formateur':
                    return redirect('core:dashboard')
            else:
                messages.error(request, f"Ce compte n'est pas enregistré comme {role_choisi}.")
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect")

    return render(request, 'account/log/log_in.html', {'form': form})


# ── Connexion avec Google ──────────────────────────────────────────
# Flux OAuth 2.0 "manuel" (sans librairie tierce) :
#   1. google_login    → redirige l'utilisateur vers l'écran de consentement Google
#   2. Google redirige vers google_callback avec un "code" temporaire
#   3. google_callback échange ce code contre un token, récupère l'email
#      via Google, puis cherche un compte existant avec cet email.
#      - trouvé      → connexion directe
#      - pas trouvé  → message d'erreur + redirection vers l'inscription
#        classique (Google ne sert ici qu'à se connecter à un compte
#        déjà existant, pas à en créer un nouveau).

GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'


def google_login(request):
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        messages.error(request, "La connexion Google n'est pas encore configurée sur ce serveur.")
        return redirect('account:log_in')

    # Jeton anti-CSRF : généré ici, vérifié au retour dans google_callback
    state = secrets.token_urlsafe(24)
    request.session['google_oauth_state'] = state

    params = {
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'prompt': 'select_account',
    }

    return redirect(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


def google_callback(request):
    # L'utilisateur a refusé l'accès, ou une erreur est survenue côté Google
    error = request.GET.get('error')
    if error:
        messages.error(request, "Connexion Google annulée.")
        return redirect('account:log_in')

    # Vérification du jeton anti-CSRF
    state = request.GET.get('state')
    if not state or state != request.session.pop('google_oauth_state', None):
        messages.error(request, "La connexion Google a échoué (session invalide). Réessayez.")
        return redirect('account:log_in')

    code = request.GET.get('code')
    if not code:
        messages.error(request, "La connexion Google a échoué.")
        return redirect('account:log_in')

    # Échange du code contre un access token
    try:
        token_data = urlencode({
            'code': code,
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
            'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI,
            'grant_type': 'authorization_code',
        }).encode('utf-8')

        token_request = urllib.request.Request(GOOGLE_TOKEN_URL, data=token_data, method='POST')
        with urllib.request.urlopen(token_request, timeout=10) as response:
            token_json = json.loads(response.read().decode('utf-8'))
        access_token = token_json.get('access_token')

        # Récupération du profil Google (email, nom, photo...)
        userinfo_request = urllib.request.Request(
            GOOGLE_USERINFO_URL,
            headers={'Authorization': f'Bearer {access_token}'},
        )
        with urllib.request.urlopen(userinfo_request, timeout=10) as response:
            google_profile = json.loads(response.read().decode('utf-8'))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError):
        messages.error(request, "Impossible de contacter Google. Réessayez plus tard.")
        return redirect('account:log_in')

    email = google_profile.get('email')
    if not email:
        messages.error(request, "Google n'a pas transmis d'adresse email.")
        return redirect('account:log_in')

    # Google ne sert qu'à se connecter à un compte EXISTANT : si l'email
    # ne correspond à aucun compte, on redirige vers l'inscription classique.
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        messages.info(
            request,
            "Aucun compte n'est associé à cette adresse Google. Créez d'abord un compte."
        )
        return redirect('account:log_up')

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    _notifier_si_profil_incomplet(user)
    messages.success(request, f"Bienvenue, {user.first_name or user.username} !")
    return redirect('core:dashboard')



# Déconnexion
@login_required
def log_out(request):
    user = request.user
    if user.role == 'admin':
        logout(request)
        return redirect('account:admin_login')

    if user.role == 'formateur' or user.role == 'institution':
        logout(request)
        return redirect('account:log_in')


# La vue qui traite la connexion des administrateurs
def adminLogin(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    
    if request.method == 'POST':
        username = request.POST.get('username').lower()
        password = request.POST.get('password')
        role_choisi = request.POST.get('role') # Récupère "admin" envoyé par l'input hidden

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # On vérifie que c'est bien un admin en base de données
            if user.role == 'admin':
                login(request, user)
                return redirect('core:dashboard') # Ou vers l'admin Django
            else:
                messages.error(request, "Accès refusé : ce compte n'est pas un administrateur.")
        else:
            messages.error(request, "Identifiants incorrects.")
    
    return render(request, 'account/log/admin_login.html')

# def adminLogin(request):
#     if request.user.is_authenticated:
#         return redirect("core:dashboard")
    
#     return render(request, 'account/log/admin_login.html')








# La vue d'inscription
def log_up(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            role = data["role"]
            
            # 1. Création de l'utilisateur
            user = User.objects.create_user(
                username=data["username"],
                email=data["email"],
                password=data["password"],
            )
            user.role = role
            user.save()

            # 2. Création du profil correspondant avec les bons champs de modèles
            if role == "formateur":
                formateur = Formateur.objects.create(
                    user=user,  # Utilise la variable corrigée
                    biographie=data.get("biographie", ""),  # Ajustez selon le nom exact dans SignUpForm
                    localisation_formateur=data.get("localisation_formateur", ""),
                    tarif_journalier=data.get("tarif_journalier", None),
                )
                # Gestion obligatoire du champ ManyToMany après la création de l'instance
                if "competences" in data:
                    formateur.competences.set(data["competences"])
                    
            elif role == "institution":
                Institution.objects.create(
                    user=user,
                    nom_organisation=data.get("nom_organisation", ""),
                    description=data.get("description", ""),
                    localisation_institution=data.get("localisation_institution", ""),
                )

            login(request, user)
            _notifier_si_profil_incomplet(user)
            messages.success(request, "Bienvenue ! Votre compte a bien été créé.")
            return redirect("core:dashboard")
        else:
            # Optionnel : pour voir l'erreur immédiatement dans votre terminal de développement
            print(form.errors)
    else:
        form = SignUpForm()

    return render(request, "account/log/log_up.html", {"form": form})




# La vue qui affiche la liste des institutions
def list_institutions(request):
    queryset = Institution.objects.all().order_by('-user__date_inscription')

    # Paramètres GET
    search_query = request.GET.get('q', '').strip()
    selected_city = request.GET.get('ville', '').strip()

    # Recherche texte
    if search_query:
        queryset = queryset.filter(
            Q(nom_organisation__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(secteur__icontains=search_query)
        )

    # Filtre ville
    if selected_city:
        queryset = queryset.filter(
            localisation_institution__iexact=selected_city
        )

    # Liste des villes disponibles pour le filtre (calculée sur l'ensemble
    # des institutions, indépendamment de la recherche/filtre en cours)
    villes_disponibles = (
        Institution.objects
        .exclude(localisation_institution='')
        .order_by('localisation_institution')
        .values_list('localisation_institution', flat=True)
        .distinct()
    )

    queryset = queryset.annotate(
        offres_ouvertes=Count('offres', filter=Q(offres__statut='publiee'), distinct=True)
    )

    # Pagination : 30 institutions par page
    paginator = Paginator(queryset, ITEMS_PAR_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    # On n'annote (besoins_tags) que les institutions de la page affichée,
    # pas tout le queryset — sinon on refait cette requête pour chaque
    # institution existante à chaque chargement de page.
    institutions = list(page_obj)
    for inst in institutions:
        inst.besoins_tags = (
            Offre.objects
            .filter(institution_id=inst, statut='publiee')
            .values_list('competences__nom', flat=True)
            .exclude(competences__nom__isnull=True)
            .distinct()[:3]
        )

    context = {
        "page_obj": page_obj,
        "institutions": institutions,
        "search_query": search_query,
        "selected_city": selected_city,
        "villes_disponibles": villes_disponibles,
        "total_count": paginator.count,
    }

    # Choix du template selon l'état de connexion
    if request.user.is_authenticated:
        template = "account/app/login_user/institutions_app.html"
    else:
        template = "account/app/not_login_user/institutions_public.html"

    return render(request, template, context)


@login_required
def detail_institution(request, pk):
    institution = get_object_or_404(Institution, pk=pk)

    offres_ouvertes = institution.offres.filter(statut='publiee').count()
    besoins_tags = (
        Offre.objects
        .filter(institution_id=institution, statut='publiee')
        .values_list('competences__nom', flat=True)
        .exclude(competences__nom__isnull=True)
        .distinct()
    )

    context = {
        "institution": institution,
        "offres_ouvertes": offres_ouvertes,
        "besoins_tags": besoins_tags,
    }

    return render(request, "account/app/login_user/institution_detail_app.html", context)





# La vue qui affiche la liste des formateurs
def list_formateurs(request):
    queryset = Formateur.objects.select_related('user').all().order_by('-user__date_inscription')

    search_query = request.GET.get('q', '').strip()
    selected_city = request.GET.get('ville', '').strip()

    if search_query:
        queryset = queryset.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(biographie__icontains=search_query) |
            Q(competences__nom__icontains=search_query)
        ).distinct()

    if selected_city:
        queryset = queryset.filter(
            localisation_formateur__iexact=selected_city
        )

    villes_disponibles = (
        Formateur.objects
        .exclude(localisation_formateur='')
        .order_by('localisation_formateur')
        .values_list('localisation_formateur', flat=True)
        .distinct()
    )

    # Pagination : 30 formateurs par page
    paginator = Paginator(queryset, ITEMS_PAR_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Notes calculées seulement pour les formateurs de la page affichée
    formateurs = list(page_obj)
    _annoter_note_par_utilisateur(formateurs, get_user=lambda f: f.user)

    context = {
        "page_obj": page_obj,
        "formateurs": formateurs,
        "search_query": search_query,
        "selected_city": selected_city,
        "villes_disponibles": villes_disponibles,
        "total_count": paginator.count,
    }

    if request.user.is_authenticated:
        template = "account/app/login_user/formateurs_app.html"
    else:
        template = "account/app/not_login_user/formateurs_public.html"

    return render(request, template, context)


def _annoter_note_par_utilisateur(objets, get_user):
    """
    Enrichit chaque objet (formateur, ...) avec .note_globale (float, None
    si aucun avis) et .nb_evaluations (int), calculés à partir de TOUTES
    les évaluations reçues par l'utilisateur lié (get_user(objet)).
    """
    if not objets:
        return

    user_ids = [get_user(o).pk for o in objets]

    stats_qs = (
        Evaluation.objects
        .filter(cible_id__in=user_ids)
        .values('cible_id')
        .annotate(moyenne=Avg('note_evaluation'), total=Count('id'))
    )
    stats_dict = {row['cible_id']: row for row in stats_qs}

    for o in objets:
        stats = stats_dict.get(get_user(o).pk, {})
        o.note_globale = round(float(stats['moyenne']), 1) if stats.get('moyenne') else None
        o.nb_evaluations = stats.get('total', 0) or 0


@login_required
def detail_formateur(request, pk):
    formateur = get_object_or_404(Formateur.objects.select_related('user'), pk=pk)

    stats = (
        Evaluation.objects
        .filter(cible=formateur.user)
        .aggregate(moyenne=Avg('note_evaluation'), total=Count('id'))
    )
    note_globale = round(float(stats['moyenne']), 1) if stats.get('moyenne') else None
    nb_evaluations = stats.get('total', 0) or 0

    avis_qs = (
        Evaluation.objects
        .filter(cible=formateur.user)
        .exclude(commentaire='')
        .select_related('auteur', 'auteur__profil_institution')
        .order_by('-date_evaluation')[:10]
    )

    avis_list = []
    for ev in avis_qs:
        institution = getattr(ev.auteur, 'profil_institution', None)
        avis_list.append({
            'note': ev.note_evaluation,
            'commentaire': ev.commentaire,
            'auteur_nom': f"{ev.auteur.first_name} {ev.auteur.last_name[:1]}." if ev.auteur.last_name else ev.auteur.first_name,
            'structure': institution.nom_organisation if institution else '',
        })

    context = {
        "formateur": formateur,
        "note_globale": note_globale,
        "nb_evaluations": nb_evaluations,
        "avis_list": avis_list,
    }

    return render(request, "account/app/login_user/formateur_detail_app.html", context)


@login_required
def parametres_profil(request):

    user = request.user
    profil_formateur = getattr(user, 'profil_formateur', None)
    profil_institution = getattr(user, 'profil_institution', None)

    profil_form = None

    if request.method == 'POST':
        user_form = ProfilUtilisateurForm(request.POST, request.FILES, instance=user)

        if user.role == 'formateur' and profil_formateur:
            profil_form = ProfilFormateurForm(request.POST, instance=profil_formateur)
        elif user.role == 'institution' and profil_institution:
            profil_form = ProfilInstitutionForm(request.POST, instance=profil_institution)

        user_form_valide = user_form.is_valid()
        profil_form_valide = profil_form.is_valid() if profil_form else True

        if user_form_valide and profil_form_valide:
            user_form.save()

            if profil_form:
                profil_form.save()

            messages.success(request, "Votre profil a bien été mis à jour.")
            return redirect('account:parametres_profil')

    else:
        user_form = ProfilUtilisateurForm(instance=user)

        if user.role == 'formateur' and profil_formateur:
            profil_form = ProfilFormateurForm(instance=profil_formateur)
        elif user.role == 'institution' and profil_institution:
            profil_form = ProfilInstitutionForm(instance=profil_institution)

    return render(request, 'account/app/login_user/parametres_profil.html', {
        'user_form': user_form,
        'profil_form': profil_form,
    })

    # {%  %}