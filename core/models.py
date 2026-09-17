from django.db import models


class Competence(models.Model):
    """
    Modèle partagé entre les apps `offre` et `formation` (relation
    Many-to-Many des deux côtés) — reste dans `core` pour cette raison,
    plutôt que d'être dupliqué ou arbitrairement rattaché à l'une des deux.
    """
    nom = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=False, blank=True, null=True)
    categorie = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ['nom']

    def __str__(self):
        return self.nom
