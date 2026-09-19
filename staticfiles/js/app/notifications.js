/* ═══════════════════════════════════════════════════════════════════
   notifications.js — Cloche in-app + Web Push
═══════════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    // ── Utilitaires ────────────────────────────────────────────────
    function getCookie(name) {
        var value = null;
        if (document.cookie && document.cookie !== '') {
            document.cookie.split(';').forEach(function (cookie) {
                var c = cookie.trim();
                if (c.substring(0, name.length + 1) === name + '=') {
                    value = decodeURIComponent(c.substring(name.length + 1));
                }
            });
        }
        return value;
    }

    function urlBase64ToUint8Array(base64String) {
        var padding = '='.repeat((4 - base64String.length % 4) % 4);
        var base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
        var rawData = window.atob(base64);
        var outputArray = new Uint8Array(rawData.length);
        for (var i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    function apiFetch(url, options) {
        options = options || {};
        options.headers = Object.assign({
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json',
        }, options.headers || {});
        return fetch(url, options).then(function (res) { return res.json(); });
    }

    // ── Cloche / liste in-app ──────────────────────────────────────
    var dropdownOpen = false;

    function renderNotifications(data) {
        var badge = document.getElementById('notifBadge');
        var list = document.getElementById('notifList');
        if (!list) return;

        if (badge) {
            if (data.non_lues > 0) {
                badge.textContent = data.non_lues > 9 ? '9+' : data.non_lues;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        }

        if (!data.notifications.length) {
            list.innerHTML = '<div class="notif-empty">Aucune notification pour l\'instant.</div>';
            return;
        }

        list.innerHTML = data.notifications.map(function (n) {
            return (
                '<div class="notif-item' + (n.lue ? '' : ' notif-item--unread') + '" data-id="' + n.id + '">' +
                    '<p class="notif-item-titre">' + escapeHtml(n.titre) + '</p>' +
                    (n.message ? '<p class="notif-item-message">' + escapeHtml(n.message) + '</p>' : '') +
                    '<span class="notif-item-date">' + n.created_at + '</span>' +
                '</div>'
            );
        }).join('');

        list.querySelectorAll('.notif-item').forEach(function (item) {
            item.addEventListener('click', function () {
                var id = item.getAttribute('data-id');
                apiFetch('/notifications/' + id + '/lu/', { method: 'POST' }).then(function () {
                    item.classList.remove('notif-item--unread');
                    chargerNotifications();
                });
            });
        });
    }

    function escapeHtml(str) {
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function chargerNotifications() {
        apiFetch('/notifications/').then(function (data) {
            if (data.ok) renderNotifications(data);
        }).catch(function () {});
    }

    function toggleDropdown() {
        var dropdown = document.getElementById('notifDropdown');
        if (!dropdown) return;
        dropdownOpen = !dropdownOpen;
        dropdown.style.display = dropdownOpen ? 'block' : 'none';
        if (dropdownOpen) chargerNotifications();
    }

    // ── Web Push ────────────────────────────────────────────────────
    function inscrirePush() {
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
        if (!window.VAPID_PUBLIC_KEY) return;

        navigator.serviceWorker.register('/sw.js').then(function (registration) {
            return registration.pushManager.getSubscription().then(function (existing) {
                if (existing) return existing;

                if (Notification.permission === 'denied') return null;

                return Notification.requestPermission().then(function (permission) {
                    if (permission !== 'granted') return null;
                    return registration.pushManager.subscribe({
                        userVisibleOnly: true,
                        applicationServerKey: urlBase64ToUint8Array(window.VAPID_PUBLIC_KEY),
                    });
                });
            });
        }).then(function (subscription) {
            if (!subscription) return;
            return apiFetch('/notifications/push/abonner/', {
                method: 'POST',
                body: JSON.stringify(subscription.toJSON ? subscription.toJSON() : subscription),
            });
        }).catch(function (err) {
            console.warn('Abonnement push impossible :', err);
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var bell = document.querySelector('.notification_icon');
        if (bell) {
            bell.addEventListener('click', function (e) {
                e.stopPropagation();
                toggleDropdown();
                // Première interaction avec la cloche = bon moment pour
                // proposer l'activation des notifications push.
                inscrirePush();
            });
        }

        document.addEventListener('click', function (e) {
            var dropdown = document.getElementById('notifDropdown');
            if (dropdown && dropdownOpen && !dropdown.contains(e.target) && e.target !== bell) {
                dropdownOpen = false;
                dropdown.style.display = 'none';
            }
        });

        var toutLireBtn = document.getElementById('notifToutLire');
        if (toutLireBtn) {
            toutLireBtn.addEventListener('click', function () {
                apiFetch('/notifications/tout-lire/', { method: 'POST' }).then(function () {
                    chargerNotifications();
                });
            });
        }

        // Badge tenu à jour même sans ouvrir la cloche
        chargerNotifications();
        setInterval(chargerNotifications, 60000);
    });
})();