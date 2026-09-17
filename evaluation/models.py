from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.conf import settings
from offre.models import Offre
from formation.models import Formation

# Create your models here.
class Evaluation(models.Model):
    TYPE_CHOICES = (
        ('candidature', 'Candidature'),
        ('formation', 'Formation'),
    )

    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name='evaluations_donnees')
    cible = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='evaluations_recues')
    offre = models.ForeignKey(Offre, on_delete=models.CASCADE, null=True, blank=True, related_name='evaluations')
    type_evaluation = models.CharField(max_length=20,choices=TYPE_CHOICES)
    formation = models.ForeignKey(Formation, on_delete=models.CASCADE, null=True, blank=True, related_name='evaluations')
    note_evaluation = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    commentaire = models.TextField(blank=True)
    date_evaluation = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'auteur',
                    'cible',
                    'offre'
                ],
                name='unique_evaluation_offre'
            ),

            models.UniqueConstraint(
                fields=[
                    'auteur',
                    'cible',
                    'formation'
                ],
                name='unique_evaluation_formation'
            )
        ]

        ordering = [
            '-date_evaluation'
        ]

    def __str__(self):

        return (
            f"{self.auteur}"
            f" → "
            f"{self.cible}"
            f" ({self.note_evaluation}/5)"
        )
    
    def clean(self):
        if (
            self.type_evaluation == 'candidature'
            and not self.offre
        ):
            raise ValidationError(
                "Une évaluation de candidature doit être liée à une offre."
            )

        if (
            self.type_evaluation == 'formation'
            and not self.formation
        ):
            raise ValidationError(
                "Une évaluation de formation doit être liée à une formation."
            )