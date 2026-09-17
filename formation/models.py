from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.utils import timezone
from django.conf import settings

from core.models import Competence


class Formation(models.Model):
    NIVEAU_CHOICES = (
        ('debutant', 'Débutant'),
        ('intermediaire', 'Intermédiaire'),
        ('avance', 'Avancé'),
    )

    CATEGORIE_CHOICES = (
        ('developpement', 'Développement'),
        ('data_ia', 'Data & IA'),
        ('design', 'Design'),
        ('cybersecurite', 'Cybersécurité'),
        ('management', 'Management'),
        ('cloud', 'Cloud'),
        ('autres', 'Autres'),
    )

    formateur = models.ForeignKey('account.Formateur', on_delete=models.CASCADE, related_name='formateurs')
    co_intervenants = models.ManyToManyField('account.Formateur', related_name='co_formateurs', blank=True)
    titre = models.CharField(max_length=200)
    description = models.TextField()
    categorie = models.CharField(max_length=50, choices=CATEGORIE_CHOICES)
    niveau = models.CharField(max_length=20, choices=NIVEAU_CHOICES)
    adresse = models.CharField(max_length=120, blank=True)
    prix = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    competences = models.ManyToManyField(Competence, related_name='formations', blank=True)
    is_published = models.BooleanField(default=False)
    date_debut = models.DateField(null=True, blank=True)
    date_cloture = models.DateField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    # 👇 NOUVEAU
    nb_places_max = models.PositiveIntegerField(default=20, verbose_name="Nombre de places maximum")
    

    # 👇 NOUVEAU — support de formation (PDF uniquement)
    support_pdf = models.FileField(upload_to='formations/supports/', null=True, blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        verbose_name="Support de formation (PDF)"
    )
 
    # 👇 NOUVEAU — override manuel du statut "terminée"
    terminee_manuelle = models.BooleanField(default=False, verbose_name="Marquée terminée manuellement")
    

    class Meta:
        ordering = ['-date_creation']
 
    def __str__(self):
        return f"{self.titre} ({self.get_categorie_display()})"
 
    def save(self, *args, **kwargs):
        # Si une seule des deux dates est renseignée, on complète l'autre
        # → une formation avec une seule date = formation d'un seul jour.
        if self.date_debut and not self.date_cloture:
            self.date_cloture = self.date_debut
        elif self.date_cloture and not self.date_debut:
            self.date_debut = self.date_cloture
 
        super().save(*args, **kwargs)
 
        # Sécurité bidirectionnelle : si le formateur principal se
        # retrouve dans co_intervenants (ex: il y était déjà avant que
        # l'admin ne le choisisse comme formateur principal), on le
        # retire automatiquement. Sans danger si déjà absent.
        if self.pk and self.formateur_id:
            self.co_intervenants.remove(self.formateur_id)
 
 
    @property
    def duree(self):
        """Durée calculée automatiquement à partir des dates."""
        if not self.date_debut or not self.date_cloture:
            return ""
 
        nb_jours = (self.date_cloture - self.date_debut).days + 1
 
        if nb_jours <= 1:
            return "1 jour"
        return f"{nb_jours} jours"
 
    @property
    def est_terminee(self):
        """
        Vraie si :
        - marquée manuellement comme terminée, OU
        - la date de clôture est dans le passé.
        """
        if self.terminee_manuelle:
            return True
        if self.date_cloture:
            return self.date_cloture < timezone.now().date()
        return False
 
    @property
    def nb_inscrits(self):
        return self.inscriptions.filter(statut='confirmee').count()
 
    @property
    def places_restantes(self):
        return max(self.nb_places_max - self.nb_inscrits, 0)
 
    @property
    def est_complete(self):
        return self.places_restantes == 0


class InscriptionFormation(models.Model):
    STATUT_CHOICES = (
        ('confirmee', 'Confirmée'),
        ('annulee', 'Annulée'),
    )

    formation = models.ForeignKey(Formation, on_delete=models.CASCADE, related_name='inscriptions')
    participant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='inscriptions_formations')
    date_inscription = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='confirmee')

    class Meta:
        unique_together = ('formation', 'participant')
        ordering = ['-date_inscription']

    def __str__(self):
        return f"{self.participant} → {self.formation.titre}"


class Attestation(models.Model):
    """
    Une attestation par inscription, générée une seule fois et stockée
    (pas de regénération : on ressert toujours le même fichier).
    """
 
    inscription = models.OneToOneField(InscriptionFormation, on_delete=models.CASCADE, related_name='attestation')
    fichier_pdf = models.FileField(upload_to='formations/attestations/')
    date_generation = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Attestation — {self.inscription}"
