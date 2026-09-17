"""
Client minimaliste pour l'API REST de GestSup.
Doc officielle : https://doc.gestsup.fr/config/#api

On ne touche JAMAIS à la base de données de GestSup directement :
tout passe par son API HTTP, qui est le mode d'intégration officiel
et supporté pour "la création de ticket depuis une application tierce".
"""

import requests
import urllib3
from django.conf import settings


class GestSupAPIError(Exception):
    """Levée si GestSup est injoignable ou renvoie une erreur métier."""
    pass


class GestSupTicketIntrouvable(GestSupAPIError):
    """Levée précisément quand le ticket n'existe plus côté GestSup
    (supprimé, base réinitialisée...). Distinct d'une simple erreur réseau
    pour permettre à l'appelant de nettoyer le suivi local au lieu de
    réessayer indéfiniment."""
    pass


def _requests_kwargs():
    """Regroupe les options communes (SSL) pour les appels à l'API GestSup."""
    verify = settings.GESTSUP_VERIFY_SSL
    if not verify:
        # Certificat auto-signé en local (XAMPP) : on désactive juste
        # l'avertissement, la vérification étant déjà volontairement coupée.
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return {'timeout': 10, 'verify': verify}


def create_gestsup_ticket(titre, description, email):
    """
    Crée un ticket dans GestSup via son API.
    Retourne le dict JSON renvoyé par GestSup (contient au moins
    'ticket_id' et 'ticket_url' en cas de succès).
    Lève GestSupAPIError en cas de problème (réseau, config, ou refus de GestSup).
    """
    base_url = (settings.GESTSUP_API_URL or '').rstrip('/')
    if not base_url:
        raise GestSupAPIError("GESTSUP_API_URL n'est pas configurée côté serveur.")

    url = f"{base_url}/api/v1/ticket/"

    # Header confirmé par le message d'erreur renvoyé par GestSup lui-même
    # ("Unable to get API Key, add X-API-KEY header") — la doc générale
    # mentionnait "api_key", mais cette instance attend bien "X-API-KEY".
    headers = {
        'X-API-KEY': settings.GESTSUP_API_KEY,
    }

    data = {
        'ticket_title': titre,
        'ticket_description': description,
        'ticket_user_mail': email,
    }

    # Le champ "type" n'est envoyé que s'il est configuré : sur certaines
    # instances GestSup, la gestion des types de tickets n'est pas activée.
    if settings.GESTSUP_DEFAULT_TICKET_TYPE:
        data['ticket_type'] = settings.GESTSUP_DEFAULT_TICKET_TYPE

    try:
        response = requests.post(url, headers=headers, data=data, **_requests_kwargs())
    except requests.exceptions.RequestException as exc:
        raise GestSupAPIError(f"Impossible de contacter GestSup : {exc}")

    try:
        payload = response.json()
    except ValueError:
        raise GestSupAPIError(
            f"Réponse inattendue de GestSup (HTTP {response.status_code}). "
            "Vérifie l'URL et la clé API."
        )

    # Convention API GestSup : code == 0 -> succès.
    if payload.get('code') != 0:
        raise GestSupAPIError(payload.get('message') or "GestSup a refusé la création du ticket.")

    return payload


def get_gestsup_ticket(ticket_id):
    """
    Relit le statut d'un ticket existant dans GestSup.
    Utile pour un futur job planifié qui détecterait la résolution
    d'un ticket et déclencherait une notification côté app.
    """
    base_url = (settings.GESTSUP_API_URL or '').rstrip('/')
    if not base_url:
        raise GestSupAPIError("GESTSUP_API_URL n'est pas configurée côté serveur.")

    url = f"{base_url}/api/v1/ticket/{ticket_id}"
    headers = {'X-API-KEY': settings.GESTSUP_API_KEY}

    try:
        response = requests.get(url, headers=headers, **_requests_kwargs())
    except requests.exceptions.RequestException as exc:
        raise GestSupAPIError(f"Impossible de contacter GestSup : {exc}")

    if response.status_code == 404:
        raise GestSupTicketIntrouvable(f"Le ticket #{ticket_id} n'existe plus dans GestSup.")

    try:
        payload = response.json()
    except ValueError:
        raise GestSupAPIError(f"Réponse inattendue de GestSup (HTTP {response.status_code}).")

    # Certaines instances renvoient un HTTP 200 avec un code d'erreur dans
    # le JSON plutôt qu'un vrai 404 — on couvre aussi ce cas.
    if payload.get('code') not in (None, 0):
        raise GestSupTicketIntrouvable(
            payload.get('message') or f"Le ticket #{ticket_id} est introuvable dans GestSup."
        )

    return payload