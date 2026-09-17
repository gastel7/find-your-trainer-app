import os


from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


from .models import Message
from account.models import User


@login_required
def chat(request, user_id=None):
    user_connecte = request.user
    
    # --- 1. MARQUER LES MESSAGES COMME LUS ---
    destinataire = None
    messages = []
    
    if user_id:
        destinataire = get_object_or_404(User, id=user_id)
        
        # On met à jour les messages reçus non lus du destinataire actif
        Message.objects.filter(
            expediteur_id=destinataire,
            destinataire_id=user_connecte,
            is_read=False
        ).update(is_read=True, date_lecture=timezone.now())
        
        # Récupération de l'historique complet (y compris les messages marqués supprimés)
        messages = Message.objects.filter(
            expediteur_id__in=[user_connecte, destinataire],
            destinataire_id__in=[user_connecte, destinataire]
        ).order_by('date_envoi')

    # --- 2. CALCUL DES CONTACTS ET DES COMPTEURS NON LUS ---
    tous_les_utilisateurs = User.objects.exclude(id=user_connecte.id)
    
    messages_recents = Message.objects.filter(
        Q(expediteur_id=user_connecte) | Q(destinataire_id=user_connecte)
    )
    
    interlocuteurs_ids = set()
    for msg in messages_recents:
        if msg.expediteur_id_id != user_connecte.id:
            interlocuteurs_ids.add(msg.expediteur_id_id)
        if msg.destinataire_id_id != user_connecte.id:
            interlocuteurs_ids.add(msg.destinataire_id_id)
            
    contacts_recents = tous_les_utilisateurs.filter(id__in=interlocuteurs_ids)
    autres_utilisateurs = tous_les_utilisateurs.exclude(id__in=interlocuteurs_ids)

    # On ajoute dynamiquement le nombre de messages non lus pour les contacts récents
    for contact in contacts_recents:
        contact.non_lus_count = Message.objects.filter(
            expediteur_id=contact,
            destinataire_id=user_connecte,
            is_read=False
        ).count()

    return render(request, 'chat/chat.html', {
        'destinataire': destinataire,
        'chat_messages': messages,
        'contacts_recents': contacts_recents,
        'autres_utilisateurs':autres_utilisateurs,
    })



# Liste des extensions strictement autorisées
EXTENSIONS_AUTORISEES = [
    # Images
    '.jpg', '.jpeg', '.png', '.gif', '.webp',
    # Documents
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt',
    # Audios (pour les vocaux et musiques)
    '.mp3', '.wav', '.ogg', '.m4a', '.webm'
]

@csrf_exempt
@login_required
def upload_chat_file(request):
    if request.method == 'POST' and request.FILES.get('fichier'):
        fichier = request.FILES['fichier']
        destinataire_id = request.POST.get('destinataire_id')
        
        # 1. Vérification de l'extension du fichier
        nom_fichier = fichier.name.lower()
        extension = os.path.splitext(nom_fichier)[1]
        
        if extension not in EXTENSIONS_AUTORISEES:
            return JsonResponse({
                'success': False, 
                'error': 'Type de fichier non autorisé. Les vidéos ne sont pas acceptées.'
            }, status=400)
            
        # 2. Sécurité supplémentaire sur le type MIME (Content-Type)
        if fichier.content_type and fichier.content_type.startswith('video/'):
            return JsonResponse({
                'success': False, 
                'error': 'Interdit : L\'envoi de vidéos n\'est pas supporté.'
            }, status=400)

        # Sauvegarde si tout est valide
        destinataire = User.objects.get(id=destinataire_id)
        message_obj = Message.objects.create(
            expediteur_id=request.user,
            destinataire_id=destinataire,
            fichier_joint=fichier,
            contenu=request.POST.get('contenu', '')
        )
        
        return JsonResponse({
            'success': True,
            'message_id': message_obj.id,
            'file_url': message_obj.fichier_joint.url,
            'file_type': message_obj.file_type
        })
        
    return JsonResponse({'success': False, 'error': 'Requête invalide'}, status=400)