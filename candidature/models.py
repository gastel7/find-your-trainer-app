from django.db import models
from offre.models import Offre
from account.models import Formateur, User
from django.conf import settings

# Create your models here.

class Candidature(models.Model):
    STATUT_CHOICES = (
        ('en_attente', 'En attente'),
        ('acceptee', 'Acceptée'),
        ('refusee', 'Refusée'),
        ('retiree', 'Retirée'),
    )

    offre = models.ForeignKey(Offre, on_delete=models.CASCADE, related_name='candidatures')
    formateur = models.ForeignKey('account.Formateur', on_delete=models.CASCADE, related_name='candidatures')
    message = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    date_candidature = models.DateTimeField(auto_now_add=True)
    cv = models.FileField(upload_to='candidatures/cv/', blank=True, null=True)

    date_traitement = models.DateTimeField(null=True,blank=True)
    traitee_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,null=True,blank=True,related_name='candidatures_traitees')
    commentaire_decision = models.TextField(blank=True) 

    # Le champ commentaire est utilisé pour permettre à l'institution de fournir une explication 
    # lors du refus d'une candidature, ou pour justifier le retrait d'une candidature par le 
    # formateur lui-même. Il peut également être utilisé pour documenter les raisons d'une 
    # acceptation, bien que cela soit moins courant. Ce champ offre une transparence accrue dans 
    # le processus de gestion des candidatures, en permettant aux parties prenantes de comprendre
    #  les décisions prises.



    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['offre_id', 'formateur_id'],
                name='unique_candidature_par_offre',
            ),
        ]
        ordering = ['-date_candidature']

    def __str__(self):
        return f"{self.formateur} → {self.offre_id} ({self.get_statut_display()})"
