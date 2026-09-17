from django.conf import settings


def vapid_public_key(request):
    """
        Rend VAPID_PUBLIC_KEY disponible dans tous les templates (dashboard.html en a besoin
        pour l'inscription au push, sans avoir à la faire passer vue par vue).
    """
    return {'VAPID_PUBLIC_KEY': settings.VAPID_PUBLIC_KEY}