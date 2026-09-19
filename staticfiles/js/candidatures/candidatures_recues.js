document.addEventListener("DOMContentLoaded", () => {

    const modal = document.getElementById("decisionModal");
    const form = document.getElementById("decisionForm");

    const title = document.getElementById("decisionTitle");
    const question = document.getElementById("decisionQuestion");
    const confirmBtn = document.getElementById("decisionConfirmButton");

    const closeButtons = document.querySelectorAll("[data-close]");

    // ==========================
    // ACCEPTER
    // ==========================

    document.querySelectorAll(".btn-accept").forEach(btn => {

        btn.addEventListener("click", () => {

            const candidatureId = btn.dataset.id;

            title.textContent =
                "Confirmer l'acceptation ?";

            question.textContent =
                "Pourquoi validez-vous cette candidature ?";

            confirmBtn.textContent =
                "Confirmer";

            form.action =
                `/candidature/${candidatureId}/accepter/`;

            modal.classList.add("show");
        });
    });

    // ==========================
    // REFUSER
    // ==========================

    document.querySelectorAll(".btn-refuse").forEach(btn => {

        btn.addEventListener("click", () => {

            const candidatureId = btn.dataset.id;

            title.textContent =
                "Confirmer le refus ?";

            question.textContent =
                "Pourquoi refusez-vous cette candidature ?";

            confirmBtn.textContent =
                "Confirmer";

            form.action =
                `/candidature/${candidatureId}/refuser/`;

            modal.classList.add("show");
        });
    });

    // ==========================
    // RETIRER
    // ==========================

    document.querySelectorAll(".btn-retire").forEach(btn => {

        btn.addEventListener("click", () => {

            const candidatureId = btn.dataset.id;

            title.textContent =
                "Confirmer le retrait ?";

            question.textContent =
                "Pourquoi retirez-vous cette candidature ?";

            confirmBtn.textContent =
                "Confirmer";

            form.action =
                `/candidature/${candidatureId}/retirer/`;

            modal.classList.add("show");
        });
    });

    // ==========================
    // FERMETURE
    // ==========================

    closeButtons.forEach(btn => {

        btn.addEventListener("click", () => {

            modal.classList.remove("show");

        });
    });

    modal.addEventListener("click", e => {

        if(e.target === modal){

            modal.classList.remove("show");

        }
    });

});