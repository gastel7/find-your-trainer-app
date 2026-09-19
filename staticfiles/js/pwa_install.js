let deferredPrompt = null;

window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    deferredPrompt = event;
});

window.addEventListener('appinstalled', () => {
    deferredPrompt = null;
});

function isIos() {
    return /iphone|ipad|ipod/.test(window.navigator.userAgent.toLowerCase());
}

function isInStandaloneMode() {
    return (
        ('standalone' in window.navigator && window.navigator.standalone) ||
        window.matchMedia('(display-mode: standalone)').matches
    );
}

document.addEventListener('DOMContentLoaded', function () {
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js').catch(function (err) {
            console.error("Échec de l'enregistrement du Service Worker :", err);
        });
    }

    // Si déjà installée, on masque la section
    if (isInStandaloneMode()) {
        document.querySelectorAll('.download_app_section').forEach(function (el) {
            el.style.display = 'none';
        });
        return;
    }

    const installButtons = document.querySelectorAll('.js-install-app');
    const iosHint = document.querySelector('.js-install-ios-hint');

    installButtons.forEach(function (btn) {
        btn.addEventListener('click', async function () {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                await deferredPrompt.userChoice;
                deferredPrompt = null;
            } else if (isIos()) {
                iosHint && iosHint.classList.add('is-visible');
            } else {
                alert("Utilise le menu de ton navigateur (⋮ ou icône d'installation dans la barre d'adresse) pour installer l'application.");
            }
        });
    });
});