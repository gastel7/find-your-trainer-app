/* ═══════════════════════════════════════════════════════════════════
   candidatures.js
   Gère le modal de décision (accepter / refuser / retirer).
   Remplace candidatures_recues.js — identifie son modal via
   #decisionModal, sans toucher à #evalModal.
═══════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function () {

    const modal      = document.getElementById('decisionModal');
    const form       = document.getElementById('decisionForm');
    const title      = document.getElementById('decisionTitle');
    const question   = document.getElementById('decisionQuestion');
    const confirmBtn = document.getElementById('decisionConfirmButton');

    // Pas de modal décision sur cette page → on sort proprement
    if (!modal) return;

    /* ── Ouvrir ────────────────────────────────────────────────── */
    function openDecision(id, cfg) {
        title.textContent      = cfg.title;
        question.textContent   = cfg.question;
        confirmBtn.textContent = 'Confirmer';
        form.action            = cfg.action;
        modal.classList.add('show');
    }

    /* ── Accepter ──────────────────────────────────────────────── */
    document.querySelectorAll('.btn-accept').forEach(function (btn) {
        btn.addEventListener('click', function () {
            openDecision(btn.dataset.id, {
                title    : "Confirmer l'acceptation ?",
                question : 'Pourquoi validez-vous cette candidature ?',
                action   : '/candidature/' + btn.dataset.id + '/accepter/'
            });
        });
    });

    /* ── Refuser ───────────────────────────────────────────────── */
    document.querySelectorAll('.btn-refuse').forEach(function (btn) {
        btn.addEventListener('click', function () {
            openDecision(btn.dataset.id, {
                title    : 'Confirmer le refus ?',
                question : 'Pourquoi refusez-vous cette candidature ?',
                action   : '/candidature/' + btn.dataset.id + '/refuser/'
            });
        });
    });

    /* ── Retirer ───────────────────────────────────────────────── */
    document.querySelectorAll('.btn-retire').forEach(function (btn) {
        btn.addEventListener('click', function () {
            openDecision(btn.dataset.id, {
                title    : 'Confirmer le retrait ?',
                question : 'Pourquoi retirez-vous cette candidature ?',
                action   : '/candidature/' + btn.dataset.id + '/retirer/'
            });
        });
    });

    /* ── Fermer ────────────────────────────────────────────────── */
    // On cible UNIQUEMENT [data-close] à l'intérieur de #decisionModal
    modal.querySelectorAll('[data-close]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            modal.classList.remove('show');
        });
    });

    modal.addEventListener('click', function (e) {
        if (e.target === modal) modal.classList.remove('show');
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') modal.classList.remove('show');
    });

});