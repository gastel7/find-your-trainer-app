/* ═══════════════════════════════════════════════════════════════════
   app.js — JS global chargé sur toutes les pages (via dashboard.html)
   Gère : dark mode · toasts · sidebar toggle · dashboard role toggle
═══════════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    /* ── 1. Dark mode ─────────────────────────────────────────────
       L'application initiale du thème (avant peinture) est gérée par
       le script inline en tête de <body> dans dashboard.html — ici on
       gère le clic sur le bouton lune ET la bascule de l'icône
       (lune visible en clair, soleil visible en sombre).
    ─────────────────────────────────────────────────────────────── */
    const DARK_KEY = 'theme';

    function syncMoonIcon() {
        var isDark = document.body.classList.contains('dark');
        var moonIcon = document.getElementById('app-moon-icon');
        var sunIcon = document.getElementById('app-sun-icon');
        if (moonIcon) moonIcon.style.display = isDark ? 'none' : '';
        if (sunIcon) sunIcon.style.display = isDark ? '' : 'none';
    }

    /* ── 2. Tout le reste après que le DOM est prêt ───────────── */
    document.addEventListener('DOMContentLoaded', function () {

        /* ── 2a. Bouton lune (dark mode toggle) ─────────────── */
        syncMoonIcon();

        document.querySelectorAll('.moonBtn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                const isDark = document.body.classList.toggle('dark');
                localStorage.setItem(DARK_KEY, isDark ? 'dark' : 'light');
                syncMoonIcon();
            });
        });

        /* ── 2b. Toasts ──────────────────────────────────────── */
        document.querySelectorAll('.toast').forEach(function (toast) {
            setTimeout(function () {
                toast.classList.add('hide');
                setTimeout(function () { toast.remove(); }, 300);
            }, 4000);
        });

        /* ── 2c. Sidebar toggle ──────────────────────────────── */
        var btnPanel     = document.querySelector('.btn_panel');
        var sidebar      = document.querySelector('.sidebar_container');
        var containerSub = document.querySelector('.container-sub');

        if (btnPanel && sidebar) {
            btnPanel.addEventListener('click', function () {
                var collapsed = sidebar.classList.toggle('sidebar--collapsed');
                if (containerSub) {
                    containerSub.classList.toggle('sidebar--collapsed', collapsed);
                }
            });
        }

        /* ── 2c-bis. Tooltips de la sidebar réduite ──────────────────
           .floting_text est en position:fixed (pour échapper au
           overflow-x:hidden de .sidebar_container qui, sinon, le
           découperait). position:fixed ne suit pas automatiquement son
           élément déclencheur : on calcule donc sa position ici, à
           chaque survol, à partir du rectangle réel de l'item survolé.
        ─────────────────────────────────────────────────────────── */
        document.querySelectorAll('.navigation li').forEach(function (li) {
            var tooltip = li.querySelector('.floting_text');
            if (!tooltip) return;

            li.addEventListener('mouseenter', function () {
                var rect = li.getBoundingClientRect();
                tooltip.style.top = (rect.top + rect.height / 2) + 'px';
                tooltip.style.left = (rect.right + 14) + 'px';
            });
        });

        /* ── 2d. Dashboard admin : toggle Formateurs / Institutions ──
           Gère les boutons #roleToggle > .role-opt[data-role]
           et bascule entre #view-formateur et #view-institution
        ─────────────────────────────────────────────────────────── */
        var roleToggle = document.getElementById('roleToggle');
        if (roleToggle) {
            var opts  = roleToggle.querySelectorAll('.role-opt');
            var views = {
                formateur   : document.getElementById('view-formateur'),
                institution : document.getElementById('view-institution')
            };

            opts.forEach(function (opt) {
                opt.addEventListener('click', function () {
                    var role = opt.dataset.role;

                    // Met à jour le bouton actif
                    opts.forEach(function (o) {
                        o.classList.toggle('is-active', o === opt);
                    });

                    // Affiche/masque les deux sections
                    Object.keys(views).forEach(function (k) {
                        var el = views[k];
                        if (!el) return;
                        el.classList.toggle('hidden', k !== role);
                    });
                });
            });
        }

    });

})();