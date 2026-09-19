/* ═══════════════════════════════════════════════════════════════════
   export.js — Exporter uniquement ce qui est affiché à l'écran
   (respecte la pagination : page 1 = 10 lignes visibles → exporte ces
   10-là ; page 2 = 3 visibles → exporte ces 3-là). Fonctionne quel que
   soit le mécanisme de pagination utilisé ailleurs (tant qu'il masque
   les cartes hors-page via display:none, ce qui est le cas standard).
═══════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function () {

    document.querySelectorAll('.js-export').forEach(function (link) {
        link.addEventListener('click', function (e) {
            e.preventDefault();

            var visibleIds = [];
            document.querySelectorAll('.candidature-card').forEach(function (card) {
                // offsetParent === null → l'élément (ou un parent) est display:none,
                // donc masqué par la pagination (peu importe son mécanisme exact).
                if (card.offsetParent !== null && card.dataset.id) {
                    visibleIds.push(card.dataset.id);
                }
            });

            var url = link.getAttribute('href');
            if (visibleIds.length > 0) {
                url += '&ids=' + visibleIds.join(',');
            }

            window.location.href = url;
        });
    });

});