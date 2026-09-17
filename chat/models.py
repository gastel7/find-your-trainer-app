import os
from django.db import models
from account.models import User

def generate_upload_path(instance, filename):
    # Organise les fichiers par type et par date
    ext = filename.split('.')[-1]
    return f"chat_files/{instance.expediteur_id.id}/{filename}"

class Message(models.Model):
    expediteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_envoyes')
    destinataire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_recus')
    contenu = models.TextField(blank=True, null=True) # Devient optionnel si on envoie juste un fichier
    
    # Nouveau champ pour les fichiers/vocaux
    fichier_joint = models.FileField(upload_to=generate_upload_path, blank=True, null=True)
    
    date_envoi = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    date_lecture = models.DateTimeField(null=True, blank=True)
    is_delete = models.BooleanField(default=False)

    @property
    def file_type(self):
        if not self.fichier_joint:
            return None
        ext = os.path.splitext(self.fichier_joint.name)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            return 'image'
        elif ext in ['.mp3', '.wav', '.ogg', '.m4a']:
            return 'audio'
        else:
            return 'document'
