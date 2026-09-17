import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from .models import Notification, PushSubscription


# ── Notifications in-app (cloche du header) ──────────────────────────

@login_required
@require_GET
def liste_notifications(request):
    notifs = Notification.objects.filter(user=request.user)[:20]
    non_lues = Notification.objects.filter(user=request.user, lue=False).count()
    return JsonResponse({
        'ok': True,
        'non_lues': non_lues,
        'notifications': [
            {
                'id': n.id,
                'titre': n.titre,
                'message': n.message,
                'url': n.url,
                'lue': n.lue,
                'created_at': n.created_at.strftime('%d/%m/%Y %H:%M'),
            }
            for n in notifs
        ],
    })


@login_required
@require_POST
def marquer_lu(request, notif_id):
    Notification.objects.filter(id=notif_id, user=request.user).update(lue=True)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def marquer_tout_lu(request):
    Notification.objects.filter(user=request.user, lue=False).update(lue=True)
    return JsonResponse({'ok': True})


# ── Web Push (abonnement navigateur) ──────────────────────────────────

@login_required
@require_POST
def save_push_subscription(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'ok': False, 'error': 'Payload invalide.'}, status=400)

    endpoint = payload.get('endpoint')
    keys = payload.get('keys', {})
    p256dh = keys.get('p256dh')
    auth = keys.get('auth')

    if not (endpoint and p256dh and auth):
        return JsonResponse({'ok': False, 'error': 'Abonnement incomplet.'}, status=400)

    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={'user': request.user, 'p256dh': p256dh, 'auth': auth},
    )
    return JsonResponse({'ok': True})


@login_required
@require_POST
def remove_push_subscription(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'ok': False}, status=400)

    endpoint = payload.get('endpoint')
    if endpoint:
        PushSubscription.objects.filter(endpoint=endpoint, user=request.user).delete()
    return JsonResponse({'ok': True})


# ── Service worker (servi à la racine du domaine pour avoir la portée
#    la plus large possible — un fichier statique sous /static/ n'aurait
#    de portée que sur /static/, pas sur tout le site) ─────────────────

@csrf_exempt
@require_GET
def service_worker(request):
    js = """
        self.addEventListener('push', function (event) {
            var data = {};
            try { data = event.data ? event.data.json() : {}; } catch (e) {}

            var title = data.title || "Notification";
            var options = {
                body: data.body || '',
                icon: '/static/img/icon-192.png',
                badge: '/static/img/icon-192.png',
                data: { url: data.url || '/' },
            };
            event.waitUntil(self.registration.showNotification(title, options));
        });

        self.addEventListener('notificationclick', function (event) {
            event.notification.close();
            var url = (event.notification.data && event.notification.data.url) || '/';
            event.waitUntil(
                clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (windowClients) {
                    for (var i = 0; i < windowClients.length; i++) {
                        var client = windowClients[i];
                        if (client.url.indexOf(url) !== -1 && 'focus' in client) {
                            return client.focus();
                        }
                    }
                    if (clients.openWindow) return clients.openWindow(url);
                })
            );
        });
        """
    return HttpResponse(js, content_type='application/javascript')