from django.conf import settings
from django.db import models


class SupportTicket(models.Model):
    """
    Trace locale d'une demande d'aide envoyée à GestSup via son API.
    On ne stocke QUE ce qui nous est utile côté app (pour afficher un
    historique à l'utilisateur, savoir où en est sa demande, etc.).
    La donnée de référence / la gestion du ticket reste entièrement
    dans GestSup — on ne duplique jamais sa base.
    """

    STATUT_ENVOYE = 'envoye'
    STATUT_RESOLU = 'resolu'
    STATUT_ERREUR = 'erreur'
    STATUT_INTROUVABLE = 'introuvable'

    STATUT_CHOICES = (
        (STATUT_ENVOYE, 'Envoyé'),
        (STATUT_RESOLU, 'Résolu'),
        (STATUT_ERREUR, 'Erreur d\'envoi'),
        (STATUT_INTROUVABLE, 'Introuvable dans GestSup'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets',)
    titre = models.CharField(max_length=200)
    description = models.TextField()
    email = models.EmailField(help_text="Email utilisé pour la création du ticket (peut différer de celui du compte).")

    gestsup_ticket_id = models.CharField(max_length=20, blank=True, null=True)
    gestsup_url = models.CharField(max_length=500, blank=True, null=True)

    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default=STATUT_ENVOYE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Demande d'aide"
        verbose_name_plural = "Demandes d'aide"

    def __str__(self):
        return f"#{self.gestsup_ticket_id or '?'} — {self.titre} ({self.user})"