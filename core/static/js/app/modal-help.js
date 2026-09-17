/* ═══════════════════════════════════════════════════════════════════
   modal-help.js — Modal "Besoin d'aide" global (AJAX, sans redirection)
   Ouvert via le bouton #i_need_help_btn du header (dashboard.html).
   Fonctions publiques : openHelpModal() / closeHelpModal()
═══════════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    function getModal() { return document.getElementById('helpModal'); }
    function getForm()  { return document.getElementById('helpForm'); }

    function resetForm() {
        var form = getForm();
        var errorEl = document.getElementById('helpError');
        var submitBtn = document.getElementById('helpSubmitBtn');
        if (form) {
            var titre = document.getElementById('helpTitre');
            var desc  = document.getElementById('helpDescription');
            if (titre) titre.value = '';
            if (desc)  desc.value  = '';
        }
        if (errorEl)   { errorEl.style.display = 'none'; errorEl.textContent = ''; }
        if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Envoyer la demande'; }
    }

    window.openHelpModal = function () {
        var modal = getModal();
        if (!modal) return;
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    };

    window.closeHelpModal = function () {
        var modal = getModal();
        if (modal) modal.classList.add('hidden');
        document.body.style.overflow = '';
        resetForm();
    };

    function showToast(message, type) {
        var container = document.getElementById('toastContainer');
        if (!container) return;
        var toast = document.createElement('div');
        toast.className = 'toast ' + (type || 'success');
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(function () {
            toast.classList.add('hide');
            setTimeout(function () { toast.remove(); }, 300);
        }, 5000);
    }

    document.addEventListener('DOMContentLoaded', function () {

        // Ouverture depuis le bouton du header
        var helpBtn = document.getElementById('i_need_help_btn');
        if (helpBtn) {
            helpBtn.addEventListener('click', function () {
                window.openHelpModal();
            });
        }

        // Overlay → fermer
        var modal = getModal();
        if (modal) {
            modal.addEventListener('click', function (e) {
                if (e.target === modal) window.closeHelpModal();
            });
        }

        // Soumission AJAX (pas de redirection)
        var form = getForm();
        if (form) {
            form.addEventListener('submit', function (e) {
                e.preventDefault();

                var submitBtn = document.getElementById('helpSubmitBtn');
                var errorEl   = document.getElementById('helpError');
                if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Envoi…'; }
                if (errorEl)   { errorEl.style.display = 'none'; }

                var body = new FormData(form);

                fetch(form.action, {
                    method: 'POST',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    body: body
                })
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    if (data.ok) {
                        window.closeHelpModal();
                        showToast(data.message || 'Demande envoyée !', 'success');
                    } else {
                        if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Envoyer la demande'; }
                        if (errorEl) {
                            errorEl.textContent = data.error || 'Une erreur est survenue.';
                            errorEl.style.display = 'block';
                        }
                    }
                })
                .catch(function () {
                    if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Envoyer la demande'; }
                    if (errorEl) {
                        errorEl.textContent = "Impossible de contacter le serveur. Vérifie ta connexion.";
                        errorEl.style.display = 'block';
                    }
                });
            });
        }
    });
})();