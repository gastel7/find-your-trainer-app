/* ═══════════════════════════════════════════════════════════════════
   modal-eval.js — Modal évaluation global (AJAX, sans redirection)
   Fonctions publiques :
     openEvalModal(type, objectId, cibleNom, noteGlobale, nbEvals, commentaire, noteExistante)
     closeEvalModal()
     openEvalCible(btn)        — co-intervenant d'une formation
     openEvalParticipant(btn)  — participant d'une formation
═══════════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    const NOTE_LABELS = {
        1: 'Très insatisfait',
        2: 'Insatisfait',
        3: 'Correct',
        4: 'Satisfait',
        5: 'Très satisfait'
    };

    /* ── Helpers internes ─────────────────────────────────────────── */
    function getModal()  { return document.getElementById('evalModal'); }
    function getForm()   { return document.getElementById('evalForm'); }

    function setStars(value) {
        document.querySelectorAll('.star-btn').forEach(function (btn) {
            var v = parseInt(btn.dataset.value, 10);
            var active = v <= value;
            btn.classList.toggle('active', active);
            var poly = btn.querySelector('polygon');
            if (poly) poly.setAttribute('fill', active ? '#f59e0b' : 'none');
            btn.style.color = active ? '#f59e0b' : '#d1d5db';
        });
        var noteInput = document.getElementById('evalNoteInput');
        var noteLabel = document.getElementById('evalNoteLabel');
        var submitBtn = document.getElementById('evalSubmitBtn');
        if (noteInput) noteInput.value = value;
        if (noteLabel) noteLabel.textContent = NOTE_LABELS[value] || '';
        if (submitBtn) submitBtn.disabled = false;
    }

    function resetModal() {
        document.querySelectorAll('.star-btn').forEach(function (btn) {
            btn.classList.remove('active');
            var poly = btn.querySelector('polygon');
            if (poly) poly.setAttribute('fill', 'none');
            btn.style.color = '#d1d5db';
        });
        var noteInput = document.getElementById('evalNoteInput');
        var noteLabel = document.getElementById('evalNoteLabel');
        var commentEl = document.getElementById('evalCommentaire');
        var submitBtn = document.getElementById('evalSubmitBtn');
        var errorEl   = document.getElementById('evalError');
        if (noteInput) noteInput.value = '';
        if (noteLabel) noteLabel.textContent = 'Sélectionnez une note';
        if (commentEl) commentEl.value = '';
        if (submitBtn) submitBtn.disabled = true;
        if (errorEl)   errorEl.style.display = 'none';
    }

    /* ── API publique ─────────────────────────────────────────────── */
    window.openEvalModal = function (type, objectId, cibleNom, noteGlobale, nbEvals, commentaire, noteExistante) {
        commentaire   = commentaire   || '';
        noteExistante = parseInt(noteExistante, 10) || 0;

        var modal = getModal();
        var form  = getForm();
        if (!modal || !form) return;

        // URL d'action
        // NB : evaluation.urls est monté à la racine (aucun préfixe
        // '/evaluations/' — ce préfixe n'existe QUE pour la page liste
        // elle-même, path('evaluations/', ...), pas comme namespace).
        form.action = type === 'candidature'
            ? '/candidature/' + objectId + '/'
            : '/evaluer-formation/'   + objectId + '/';

        // En-tête
        var eyebrow = document.getElementById('evalModalType');
        var title   = document.getElementById('evalModalTitle');
        if (eyebrow) eyebrow.textContent = type === 'candidature'
            ? 'Évaluation · Candidature'
            : 'Évaluation · Formation';
        if (title) title.textContent = 'Évaluer ' + cibleNom;

        // Stats cible
        var note   = parseFloat(noteGlobale) || 0;
        var filled = Math.round(note);
        var noteEl  = document.getElementById('evalCibleNote');
        var countEl = document.getElementById('evalCibleCount');
        var starsEl = document.getElementById('evalCibleStars');
        if (noteEl)  noteEl.textContent  = note > 0 ? note.toFixed(1) : '—';
        if (countEl) countEl.textContent = nbEvals > 0 ? nbEvals + ' avis' : 'Aucun avis';
        if (starsEl) starsEl.textContent = '★'.repeat(filled) + '☆'.repeat(5 - filled);

        // Pré-remplir
        resetModal();
        if (noteExistante > 0) setStars(noteExistante);
        var commentEl = document.getElementById('evalCommentaire');
        if (commentEl) commentEl.value = commentaire;

        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    };

    window.closeEvalModal = function () {
        var modal = getModal();
        if (modal) modal.classList.add('hidden');
        document.body.style.overflow = '';
        resetModal();
    };

    /* ── Formation : co-intervenant ──────────────────────────────── */
    window.openEvalCible = function (btn) {
        window.openEvalModal(
            'formation', btn.dataset.formationId,
            btn.dataset.cibleNom || '',
            parseFloat(btn.dataset.note) || 0,
            parseInt(btn.dataset.count, 10) || 0,
            '', 0
        );
        var form = getForm();
        if (form) form.action = '/evaluer-formation/' + btn.dataset.formationId
            + '/?cible=' + btn.dataset.cibleId;
    };

    /* ── Formation : participant ──────────────────────────────────── */
    window.openEvalParticipant = function (btn) {
        window.openEvalModal(
            'formation', btn.dataset.formationId,
            btn.dataset.cibleNom || '',
            parseFloat(btn.dataset.note) || 0,
            parseInt(btn.dataset.count, 10) || 0,
            '', 0
        );
        var form = getForm();
        if (form) form.action = '/evaluer-formation/' + btn.dataset.formationId
            + '/?participant=' + btn.dataset.participantId;
    };

    /* ── Soumission AJAX ──────────────────────────────────────────── */
    document.addEventListener('DOMContentLoaded', function () {

        // Étoiles
        var allBtns = document.querySelectorAll('.star-btn');
        allBtns.forEach(function (btn) {
            btn.addEventListener('mouseenter', function () {
                var v = parseInt(btn.dataset.value, 10);
                allBtns.forEach(function (b) {
                    b.style.color = parseInt(b.dataset.value, 10) <= v ? '#f59e0b' : '#d1d5db';
                });
            });

            btn.addEventListener('mouseleave', function () {
                var current = parseInt(
                    (document.getElementById('evalNoteInput') || {}).value || '0', 10
                );
                allBtns.forEach(function (b) {
                    b.style.color = parseInt(b.dataset.value, 10) <= current ? '#f59e0b' : '#d1d5db';
                });
            });

            btn.addEventListener('click', function () {
                setStars(parseInt(btn.dataset.value, 10));
            });
        });

        // Overlay → fermer
        var modal = getModal();
        if (modal) {
            modal.addEventListener('click', function (e) {
                if (e.target === modal) window.closeEvalModal();
            });
        }

        // Soumission AJAX (pas de redirection)
        var form = getForm();
        if (form) {
            form.addEventListener('submit', function (e) {
                e.preventDefault();

                var submitBtn = document.getElementById('evalSubmitBtn');
                var errorEl   = document.getElementById('evalError');
                if (submitBtn) submitBtn.disabled = true;
                if (errorEl)   errorEl.style.display = 'none';

                var csrfToken = form.querySelector('[name=csrfmiddlewaretoken]');

                // Construit l'URL avec les params GET éventuels
                var url    = form.action;
                var urlObj = new URL(url, window.location.origin);

                var body = new FormData(form);

                // Transfère les query params GET en champs POST
                urlObj.searchParams.forEach(function (val, key) {
                    body.set(key, val);
                });

                fetch(url, {
                    method: 'POST',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    body: body
                })
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    if (data.ok) {
                        window.closeEvalModal();
                        // Toast de succès si disponible
                        var container = document.getElementById('toastContainer');
                        if (container) {
                            var toast = document.createElement('div');
                            toast.className = 'toast success';
                            toast.textContent = data.message || 'Évaluation enregistrée !';
                            container.appendChild(toast);
                            setTimeout(function () {
                                toast.classList.add('hide');
                                setTimeout(function () { toast.remove(); }, 300);
                            }, 4000);
                        }
                    } else {
                        if (errorEl) {
                            errorEl.textContent = data.error || 'Une erreur est survenue.';
                            errorEl.style.display = 'block';
                        }
                        if (submitBtn) submitBtn.disabled = false;
                    }
                })
                .catch(function () {
                    if (errorEl) {
                        errorEl.textContent = 'Erreur réseau, veuillez réessayer.';
                        errorEl.style.display = 'block';
                    }
                    if (submitBtn) submitBtn.disabled = false;
                });
            });
        }

        // Touche Échap
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') window.closeEvalModal();
        });

    });

})();