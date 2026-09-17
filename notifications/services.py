"""
Point d'entrée UNIQUE pour notifier un utilisateur, peu importe le
déclencheur (ticket GestSup résolu, nouvelle candidature, etc.) :

    from notifications.services import notifier_utilisateur
    notifier_utilisateur(user, "Titre", "Message", url="/mes-demandes/")

Ça fait 2 choses :
  1. Crée toujours une Notification in-app (cloche du header)
  2. Tente en plus un Web Push (écran verrouillé/notif système) si
     l'utilisateur a au moins un abonnement enregistré — silencieux si
     l'envoi push échoue (l'in-app reste dans tous les cas)
"""

import json
import logging

from django.conf import settings

from .models import Notification, PushSubscription

logger = logging.getLogger(__name__)


def notifier_utilisateur(user, titre, message='', url=''):
    notification = Notification.objects.create(
        user=user, titre=titre, message=message, url=url,
    )
    _envoyer_push(user, titre, message, url)
    return notification


def _envoyer_push(user, titre, message, url):
    if not settings.VAPID_PRIVATE_KEY_PATH:
        # Push pas configuré (clés VAPID absentes) : on ne fait que l'in-app.
        return

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.warning("pywebpush n'est pas installé — notification push ignorée (pip install pywebpush).")
        return

    payload = json.dumps({
        'title': titre,
        'body': message,
        'url': url or '/',
    })

    subscriptions = PushSubscription.objects.filter(user=user)
    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub.to_subscription_info(),
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY_PATH,
                vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}"},
            )
        except WebPushException as exc:
            # 410/404 = l'abonnement n'est plus valide (désinstallé, expiré...) → on le supprime.
            status = getattr(exc.response, 'status_code', None)
            if status in (404, 410):
                sub.delete()
            else:
                logger.warning("Échec envoi push à %s : %s", user, exc)