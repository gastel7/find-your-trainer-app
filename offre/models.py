from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from dateutil.relativedelta import relativedelta  # Import requis pour le calcul exact mois/ans

from core.models import Competence


class Offre(models.Model):
    TYPE_CHOICES = (
        ('intra', 'Intra'),
        ('inter', 'Inter'),
        ('mission_longue', 'Mission longue'),
    )

    STATUT_CHOICES = (
        ('brouillon', 'Brouillon'),
        ('publiee', 'Publiée'),
        ('cloturee', 'Clôturée'),
        ('archivee', 'Archivée'),
    )

    institution = models.ForeignKey('account.Institution', on_delete=models.CASCADE, related_name='offres')
    titre = models.CharField(max_length=200)
    description = models.TextField()
    type_offre = models.CharField(max_length=20, choices=TYPE_CHOICES)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='brouillon')
    competences = models.ManyToManyField(Competence, related_name='offres', blank=True)
    localisation = models.CharField(max_length=120, blank=True)
    duree = models.CharField(max_length=80, blank=True, null=True, editable=False,)
    nb_max_de_candidatures = models.PositiveIntegerField(default=30)
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    date_publication = models.DateTimeField(auto_now_add=True)
    date_debut = models.DateField(null=True, blank=True)
    date_cloture = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-date_publication']

    def __str__(self):
        return self.titre   

    
    # On garde le champ duree propre qui stockera le texte définitif

    def save(self, *args, **kwargs):
        if self.date_debut and self.date_cloture:
            # 1. Calcul de la différence exacte (années, mois, jours)
            diff = relativedelta(self.date_cloture, self.date_debut)
            
            # 2. Logique d'affichage selon l'écart
            if diff.years > 0:
                if diff.years == 1:
                    self.duree = "1 an"
                else:
                    self.duree = f"{diff.years} ans"
                    
            elif diff.months > 0:
                self.duree = f"{diff.months} mois"  # 'mois' prend toujours un 's'
                
            else:
                if diff.days <= 1:
                    self.duree = "1 jour"
                else:
                    self.duree = f"{diff.days} jours"
        else:
            self.duree = "Durée non spécifiée"

        # 3. Sauvegarde finale en base de données
        super().save(*args, **kwargs)
