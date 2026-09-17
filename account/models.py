from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import Avg

# Create your models here.
"""
Application : account
Gestion des utilisateurs (User, Formateur, Institution).

NB :
- On garde le modèle User basé sur AbstractUser (username + email + password).
- Les profils Formateur / Institution sont reliés en OneToOne au User.
- Les compétences sont gérées via une relation ManyToMany vers core.Competence
  (déclarée en string pour éviter les imports circulaires).
"""


class User(AbstractUser):
    ROLE_CHOICES = (
        ('formateur', 'Formateur'),
        ('institution', 'Institution'),
        ('admin', 'Administrateur'),
    )
    # Suppression de la redéclaration inutile de 'username' (AbstractUser le gère déjà)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    profile_picture = models.ImageField(upload_to='users/photos/', null=True, blank=True)
    date_inscription = models.DateTimeField(auto_now_add=True)

    # Informations personnelles (première_nom / nom viennent déjà d'AbstractUser)
    CIVILITE_CHOICES = (
        ('m', 'M.'),
        ('mme', 'Mme'),
        ('autre', 'Autre / Préfère ne pas préciser'),
    )
    civilite = models.CharField(max_length=10, choices=CIVILITE_CHOICES, blank=True)
    date_naissance = models.DateField(null=True, blank=True)
    nationalite = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.username} : ({self.role})"

    def save(self, *args, **kwargs):
        # Un superuser Django créé sans rôle (ex: via `createsuperuser`,
        # qui ne demande pas ce champ) devient automatiquement admin —
        # sinon les vérifications `role == 'admin'` échouent silencieusement
        # partout dans l'app alors que la personne EST bien administratrice.
        if self.is_superuser and not self.role:
            self.role = 'admin'
        super().save(*args, **kwargs)

    @property
    def age(self):
        """Calculé à partir de date_naissance plutôt que stocké en dur,
        pour ne jamais devenir obsolète."""
        if not self.date_naissance:
            return None
        from datetime import date
        today = date.today()
        return today.year - self.date_naissance.year - (
            (today.month, today.day) < (self.date_naissance.month, self.date_naissance.day)
        )

    @property
    def note_globale(self):
        moyenne = (
            self.evaluations_recues
            .aggregate(
                Avg(
                    'note_evaluation'
                )
            )['note_evaluation__avg']
        )

        return round(
            moyenne,
            1
        ) if moyenne else 0




class Formateur(models.Model):
    # Changement du nom en 'user' + Ajout de primary_key=True
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil_formateur', limit_choices_to={'role': 'formateur'}, primary_key=True)
    biographie = models.TextField(blank=True)
    competences = models.ManyToManyField('core.Competence', related_name='formateurs', blank=True)
    localisation_formateur = models.CharField(max_length=120, blank=True)
    tarif_journalier = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    experience_annees = models.PositiveIntegerField(null=True, blank=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    titre_professionnel = models.CharField(max_length=150, blank=True)
    delai_reponse = models.CharField(max_length=30, blank=True, help_text="Ex : ~4h, ~1 jour")
    disponibilite = models.CharField(max_length=50, blank=True, help_text="Ex : 2 sem., Immédiate")
    langues = models.CharField(max_length=100, blank=True, help_text="Ex : FR, EN")

    def __str__(self):
        # return f"{self.user.username} et a pour compétences : {self.competences.all()} "
        if   self.user.last_name and self.user.first_name :
            return f"{self.user.first_name} {self.user.last_name}"
        else :
            return f"{self.user.username}"


class Institution(models.Model):
    # Changement du nom en 'user' + Ajout de primary_key=True
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profil_institution', 
        limit_choices_to={'role': 'institution'},
        primary_key=True
    )
    nom_organisation = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    localisation_institution = models.CharField(max_length=120, blank=True)
    site_web = models.URLField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    secteur = models.CharField(max_length=100, blank=True, help_text="Ex : Enseignement supérieur, E-santé")
    taille_effectif = models.CharField(max_length=50, blank=True, help_text="Ex : 500+ collaborateurs")

    def __str__(self):
        return f"{self.nom_organisation}"
        # return f"{self.nom_organisation}  appartient à {self.user.username.upper()}"



















# class User(AbstractUser):
#     ROLE_CHOICES = (
#         ('formateur', 'Formateur'),
#         ('institution', 'Institution'),
#         ('admin', 'Administrateur'),
#     )

#     username = models.CharField(max_length=150, unique=True)
#     role = models.CharField(max_length=20, choices=ROLE_CHOICES)
#     photo = models.ImageField(upload_to='users/photos/', null=True, blank=True)
#     date_inscription = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.username}"


# class Formateur(models.Model):
#     user_id = models.OneToOneField(User, on_delete=models.CASCADE, related_name='formateur', limit_choices_to={'role': 'formateur'})
#     biographie = models.TextField(blank=True)
#     competences = models.ManyToManyField('core.Competence', related_name='formateurs', blank=True,)
#     localisation = models.CharField(max_length=120, blank=True)
#     tarif_journalier = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
#     experience_annees = models.PositiveIntegerField(null=True, blank=True)
#     telephone = models.CharField(max_length=20, blank=True, null=True)
#     is_verified = models.BooleanField(default=False)

#     def __str__(self):
#         return f"Formateur : {self.user_id.username}"


# class Institution(models.Model):
#     user_id = models.OneToOneField(User, on_delete=models.CASCADE, related_name='institution', limit_choices_to={'role': 'institution'})
#     nom_organisation = models.CharField(max_length=200)
#     description = models.TextField(blank=True)
#     localisation = models.CharField(max_length=120, blank=True)
#     site_web = models.URLField(blank=True, null=True)
#     is_verified = models.BooleanField(default=False)

#     def __str__(self):
#         return self.nom_organisation



# class User(AbstractUser):
#     ROLE_CHOICES = (
#         ('formateur', 'Formateur'),
#         ('institution', 'Institution'),
#         ('admin', 'Administrateur'),
#     )
#     role = models.CharField(max_length=20, choices=ROLE_CHOICES)









# class User(AbstractUser):
#     ROLE_CHOICES = (
#         ('formateur', 'Formateur'),
#         ('institution', 'Institution'),
#         ('admin', 'Administrateur'),
#     )

#     username = models.CharField(max_length=150, unique=True)
#     role = models.CharField(max_length=20, choices=ROLE_CHOICES)
#     photo = models.ImageField(upload_to='users/photos/', null=True, blank=True)
#     date_inscription = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.username}"


# class Formateur(models.Model):
#     user_id = models.OneToOneField(User, on_delete=models.CASCADE, related_name='formateur', limit_choices_to={'role': 'formateur'})
#     biographie = models.TextField(blank=True)
#     competences = models.ManyToManyField('core.Competence', related_name='formateurs', blank=True,)
#     localisation = models.CharField(max_length=120, blank=True)
#     tarif_journalier = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
#     experience_annees = models.PositiveIntegerField(null=True, blank=True)
#     telephone = models.CharField(max_length=20, blank=True, null=True)
#     is_verified = models.BooleanField(default=False)

#     def __str__(self):
#         return f"Formateur : {self.user_id.username}"


# class Institution(models.Model):
#     user_id = models.OneToOneField(User, on_delete=models.CASCADE, related_name='institution', limit_choices_to={'role': 'institution'})
#     nom_organisation = models.CharField(max_length=200)
#     description = models.TextField(blank=True)
#     localisation = models.CharField(max_length=120, blank=True)
#     site_web = models.URLField(blank=True, null=True)
#     is_verified = models.BooleanField(default=False)

#     def __str__(self):
#         return self.nom_organisation



# class User(AbstractUser):
#     ROLE_CHOICES = (
#         ('formateur', 'Formateur'),
#         ('institution', 'Institution'),
#         ('admin', 'Administrateur'),
#     )
#     role = models.CharField(max_length=20, choices=ROLE_CHOICES)