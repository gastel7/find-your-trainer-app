// =================================================================
// 0. CALCUL DYNAMIQUE DE LA HAUTEUR DISPONIBLE POUR LE CHAT
// =================================================================
// dashboard.html (header + sidebar "Espace") n'est pas modifiable ici sans
// impacter les autres pages. Au lieu de ça, on mesure en JS l'espace que
// ces éléments fixes prennent réellement au-dessus de .app-container, et
// on force sa hauteur via une variable CSS. Comme le calcul se fait par
// rapport à la fenêtre (100vh) et pas par rapport aux parents, ça marche
// quelle que soit la structure du template partagé.
function ajusterHauteurChat() {
    const container = document.querySelector('.app-container');
    if (!container) return;
    const offsetTop = container.getBoundingClientRect().top;
    document.documentElement.style.setProperty('--chat-top-offset', offsetTop + 'px');
}
ajusterHauteurChat();
window.addEventListener('load', ajusterHauteurChat);
window.addEventListener('resize', ajusterHauteurChat);

// =================================================================
// 1. GESTION DES LISTES DE CONTACTS (Visuel & Recherche)
// =================================================================
const toggleBtn = document.getElementById('toggle-contacts-btn');
const recentList = document.getElementById('recent-chats-list');
const allUsersList = document.getElementById('all-users-list');
const searchInput = document.getElementById('search-contact');

if (toggleBtn && recentList && allUsersList) {
    toggleBtn.addEventListener('click', function() {
        const isShowingAll = recentList.classList.contains('hidden');
        if (isShowingAll) {
            recentList.classList.remove('hidden');
            allUsersList.classList.add('hidden');
            toggleBtn.innerText = '＋';
        } else {
            recentList.classList.add('hidden');
            allUsersList.classList.remove('hidden');
            toggleBtn.innerText = '✕';
        }
    });
}

if (searchInput) {
    searchInput.addEventListener('input', function(e) {
        const term = e.target.value.toLowerCase().trim();
        const activeList = recentList.classList.contains('hidden') ? allUsersList : recentList;
        const items = activeList.getElementsByClassName('conversation-item');

        Array.from(items).forEach(function(item) {
            const usernameZone = item.querySelector('.username');
            if (usernameZone) {
                const username = usernameZone.innerText.toLowerCase();
                item.style.setProperty('display', username.includes(term) ? 'flex' : 'none', 'important');
            }
        });
    });
}

// =================================================================
// 2. ACTIVATION DU WEBSOCKET & CORE MESSAGERIE
// =================================================================
if (typeof userId !== 'undefined' && userId !== null && userId !== "" && userId !== "None") {

    const chatSocket = new WebSocket('ws://' + window.location.host + '/ws/chat/' + userId + '/');
    const messagesDiv = document.getElementById('messages');
    const form = document.getElementById('chat-form');
    const input = document.getElementById('message-input');
    const fileInput = document.getElementById('file-input');
    const voiceBtn = document.getElementById('voice-btn');

    let mediaRecorder;
    let audioChunks = [];

    // POSITIONNEMENT INITIAL DU SCROLL (comportement type WhatsApp)
    // Par défaut un conteneur scrollable démarre en haut (messages les plus
    // anciens). On le repositionne tout en bas dès le chargement pour voir
    // les messages récents et pouvoir écrire directement.
    function scrollMessagesToBottom() {
        if (messagesDiv) {
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    }
    scrollMessagesToBottom();
    // Sécurité : si la conversation contient des images/audios, leur
    // chargement peut changer la hauteur après coup — on recale une fois
    // que toutes les ressources de la page sont chargées.
    window.addEventListener('load', scrollMessagesToBottom);

    // RÉCUPÉRATION EN TEMPS RÉEL (Messages, Médias & Suppressions)
    chatSocket.onmessage = function(e){
        const data = JSON.parse(e.data);
        
        // Traitement de la suppression
        if (data.action === 'message_deleted') {
            const targetWrapper = document.getElementById(`msg-${data.message_id}`);
            if (targetWrapper) {
                const bubble = targetWrapper.querySelector('.message-bubble');
                if (bubble) {
                    bubble.classList.add('deleted-bubble');
                    bubble.innerHTML = `<p class="deleted-text"><i>Ce message a été supprimé</i></p>`;
                }
            }
            return;
        }

        // Insertion d'un nouveau message standard ou multimédia
        const wrapper = document.createElement('div');
        wrapper.classList.add('message-wrapper');
        if (data.message_id) wrapper.id = `msg-${data.message_id}`;
        
        const isMe = (data.sender_id == currentUserId);
        wrapper.classList.add(isMe ? 'sent' : 'received');
        
        const bubble = document.createElement('div');
        bubble.classList.add('message-bubble');
        
        let mediaHtml = '';
        if (data.file_url) {
            if (data.file_type === 'image') {
                mediaHtml = `<img src="${data.file_url}" class="chat-image" alt="Image jointe">`;
            } else if (data.file_type === 'audio') {
                mediaHtml = `<audio controls class="chat-audio"><source src="${data.file_url}" type="audio/mpeg"></audio>`;
            } else if (data.file_type === 'document') {
                mediaHtml = `<div class="chat-document"><span class="doc-icon">📄</span><a href="${data.file_url}" target="_blank" download>Télécharger</a></div>`;
            }
        }

        let texteHtml = data.message ? `<p>${data.message}</p>` : '';
        let deleteBtnHtml = (isMe && data.message_id) ? `<button class="delete-msg-btn" data-id="${data.message_id}">×</button>` : '';
        
        const timeStr = new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
        const checkMark = isMe ? ` <span class="status-check">✓</span>` : '';

        bubble.innerHTML = `${mediaHtml}${texteHtml}${deleteBtnHtml}<span class="message-time">${timeStr}${checkMark}</span>`;
        wrapper.appendChild(bubble);
        
        if (messagesDiv) {
            messagesDiv.appendChild(wrapper);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    };

    // ENVOI DU TEXTE VIA FORMULAIRE
    if (form && input) {
        form.addEventListener('submit', function(e){
            e.preventDefault();
            const message = input.value.trim();
            if(message === '') return;

            if(chatSocket.readyState === WebSocket.OPEN){
                chatSocket.send(JSON.stringify({ 'message': message }));
                input.value = '';
                deplacerContactAuTop();
            }
        });
    }

    // INTERCEPTION DES CLICS DE SUPPRESSION
    if (messagesDiv) {
        messagesDiv.addEventListener('click', function(e) {
            if (e.target.classList.contains('delete-msg-btn')) {
                const messageId = e.target.getAttribute('data-id');
                if (confirm("Voulez-vous vraiment supprimer ce message ?") && chatSocket.readyState === WebSocket.OPEN) {
                    chatSocket.send(JSON.stringify({ 'action': 'delete_message', 'message_id': messageId }));
                }
            }
        });
    }

    // INTERDICTION DES VIDÉOS & ENVOI VIA HTTP POST (FETCH)
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;

            // Sécurité : Interdiction stricte des formats vidéos
            if (file.type.startsWith('video/') || ['.mp4', '.avi', '.mov', '.mkv'].some(ext => file.name.toLowerCase().endsWith(ext))) {
                alert("❌ Les fichiers vidéos ne sont pas acceptés.");
                fileInput.value = '';
                return;
            }

            traiterEtEnvoyerFichier(file);
        });
    }

    // GESTION ENREGISTREUR VOCAL (MICRO)
    if (voiceBtn) {
        voiceBtn.addEventListener('click', async function() {
            if (!mediaRecorder || mediaRecorder.state === "inactive") {
                // Démarrage de l'enregistrement
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];

                    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                    
                    mediaRecorder.onstop = () => {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/mp3' });
                        const audioFile = new File([audioBlob], "vocal.mp3", { type: 'audio/mp3' });
                        traiterEtEnvoyerFichier(audioFile);
                        // Fermeture propre des pistes du micro
                        stream.getTracks().forEach(track => track.stop());
                    };

                    mediaRecorder.start();
                    voiceBtn.classList.add('recording-active');
                    voiceBtn.title = "Arrêter l'enregistrement";
                } catch (err) {
                    alert("🎙️ Impossible d'accéder au micro : " + err.message);
                }
            } else {
                // Arrêt de l'enregistrement
                mediaRecorder.stop();
                voiceBtn.classList.remove('recording-active');
                voiceBtn.title = "Enregistrer un vocal";
            }
        });
    }

    // FONCTION COMMUNE D'UPLOAD HTTP POST POUR MULTIMÉDIA
    function traiterEtEnvoyerFichier(fileInstance) {
        const formData = new FormData();
        formData.append('fichier', fileInstance);
        formData.append('destinataire_id', userId);

        fetch('/chat/upload/', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success && chatSocket.readyState === WebSocket.OPEN) {
                // Notification WebSocket immédiate après succès de sauvegarde en BDD
                chatSocket.send(JSON.stringify({
                    'message': '', // Pas de texte additionnel
                    'file_url': data.file_url,
                    'file_type': data.file_type,
                    'message_id': data.message_id
                }));
                if(fileInput) fileInput.value = ''; // Reset l'input fichier
                deplacerContactAuTop();
            } else {
                alert("Erreur lors de l'envoi : " + (data.error || "Inconnue"));
            }
        })
        .catch(err => console.error("Erreur d'upload :", err));
    }

    // LOGIQUE DE DÉPLACEMENT DU CONTACT
    function deplacerContactAuTop() {
        const activeLink = document.querySelector(`#all-users-list a[href*="/chat/${userId}/"]`);
        if (activeLink) {
            const recentListContainer = document.getElementById('recent-chats-list');
            const emptyMsg = recentListContainer.querySelector('.empty-message');
            if (emptyMsg) emptyMsg.remove();
            
            const preview = activeLink.querySelector('.preview-text');
            if (preview) preview.innerText = "Nouveau message...";
            
            const avatar = activeLink.querySelector('.avatar');
            if (avatar) avatar.classList.remove('new-user');
            
            recentListContainer.appendChild(activeLink);
        }
    }
}