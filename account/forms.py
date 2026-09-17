from django import forms
from account.models import User, Formateur, Institution
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from core.models import Competence 



User = get_user_model()


class LoginForm(forms.Form):
    username = forms.CharField(label="Nom d'utilisateur")
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput())


ROLE_CHOICES = (
    ("formateur", "Je suis formateur"),
    ("institution", "Je suis institution"),
)


class SignUpForm(forms.Form):
    # --- Choix du rôle ---
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        initial="formateur",
        widget=forms.RadioSelect(attrs={"class": "role-selector"}),
    )

    # --- Compte (AbstractUser) ---
    username = forms.CharField(
        label="Nom d'utilisateur",
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "amelie.laurent"}),
        help_text="Identifiant unique pour vous connecter.",
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"placeholder": "vous@organisation.com"}),
    )
    password = forms.CharField(
        label="Mot de passe",
        min_length=8,
        widget=forms.PasswordInput(attrs={"placeholder": "Minimum 8 caractères"}),
    )

    # --- Profil formateur (Renommé 'biographie' pour matcher le modèle) ---
    biographie = forms.CharField(
        label="Bio",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Présentez-vous en quelques lignes…", "class": "field-formateur"}),
    )
    competences = forms.CharField(
        label="Compétences",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Python, Machine Learning, Data Viz", "class": "field-formateur"}),
        help_text="Séparez les compétences par des virgules.",
    )
    localisation_formateur = forms.CharField(
        label="Localisation",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Paris", "class": "field-formateur"}),
    )

    titre_professionnel = forms.CharField(
        label="Titre Professionnel",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Developpeur Django Senior", "class": "field-formateur"}),
    )

    tarif_journalier = forms.DecimalField(
        label="Tarif journalier (€)",
        required=False,
        min_value=0,
        max_digits=8,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"placeholder": "650", "class": "field-formateur"}),
    )


    # --- Profil institution ---
    nom_organisation = forms.CharField(
        label="Nom de l'organisation",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "École 42", "class": "field-institution"}),
    )
    description = forms.CharField(
        label="Description",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Décrivez votre organisation et vos besoins…", "class": "field-institution"}),
    )
    localisation_institution = forms.CharField(
        label="Localisation",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Paris", "class": "field-institution"}),
    )

    # --- CGU ---
    cgu = forms.BooleanField(
        label="J'accepte les conditions d'utilisation et la politique de confidentialité.",
        required=True,
        error_messages={"required": "Vous devez accepter les conditions d'utilisation."},
    )

    # ---- Validations individuelles ----
    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if username.lower() == "admin":
            raise ValidationError("Ce nom d'utilisateur est réservé.")
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Ce nom d'utilisateur est déjà pris.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Un compte existe déjà avec cet email.")
        return email

    def clean_password(self):
        pwd = self.cleaned_data.get("password")
        if pwd:
            validate_password(pwd)
        return pwd

    # ---- Validation conditionnelle (Formateur vs Institution) ----
    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")

        if role == "formateur":
            # Liste des champs obligatoires pour le formateur
            required_fields = {
                "biographie": "La biographie est requise pour un formateur.",
                "competences": "Veuillez renseigner au moins une compétence.",
                "localisation_formateur": "La localisation est requise.",
                "tarif_journalier": "Le tarif journalier est requis.",
            }
            # Validation et transformation de la chaîne de compétences en objets réels
            comp_text = cleaned_data.get("competences", "").strip()
            if comp_text:
                # Découpage par virgule, nettoyage des espaces, suppression des doublons/vides
                names = list(set([c.strip() for c in comp_text.split(",") if c.strip()]))
                # Récupération ou création automatique des instances de Competence en BDD
                competence_instances = [
                    Competence.objects.get_or_create(nom__iexact=name, defaults={"nom": name})[0]
                    for name in names
                ]
                # On remplace le texte par la liste d'objets pour la vue
                cleaned_data["competences"] = competence_instances

        elif role == "institution":
            # Liste des champs obligatoires pour l'institution
            required_fields = {
                "nom_organisation": "Le nom de l'organisation est requis.",
                "description": "La description est requise.",
                "localisation_institution": "La localisation de l'institution est requise.",
            }
        else:
            required_fields = {}

        # Application stricte des erreurs sur les champs manquants selon le rôle choisi
        for field, error_msg in required_fields.items():
            if not cleaned_data.get(field):
                self.add_error(field, error_msg)

        return cleaned_data



class ProfilUtilisateurForm(forms.ModelForm):
    """Champs communs à tout le monde (formateur, institution, admin) —
    la section "Informations personnelles" de la page Paramètres."""

    class Meta:
        model = User
        fields = [
            'username', 'email', 'profile_picture',
            'civilite', 'first_name', 'last_name', 'date_naissance', 'nationalite',
        ]
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': "Nom d'utilisateur",
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@exemple.com',
            }),
            'profile_picture': forms.FileInput(attrs={
                'accept': 'image/png, image/jpeg',
                'id': 'id_profile_picture',
            }),
            'civilite': forms.Select(attrs={
                'class': 'form-control',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Prénom',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom',
            }),
            'date_naissance': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'nationalite': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : Congolaise, Française...',
            }),
        }
 
 
class ProfilFormateurForm(forms.ModelForm):
    """Champs spécifiques au profil formateur."""
 
    class Meta:
        model = Formateur
        fields = [
            'titre_professionnel',
            'biographie',
            'competences',
            'localisation_formateur',
            'tarif_journalier',
            'telephone',
            'experience_annees',
            'delai_reponse',
            'disponibilite',
            'langues',
        ]
        widgets = {
            'titre_professionnel': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : Développeur Full Stack',
            }),
            'biographie': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Parlez de votre parcours, votre expertise...',
            }),
            'competences': forms.SelectMultiple(attrs={
                'class': 'select2-multiple',
                'id': 'select-competences-profil',
            }),
            'localisation_formateur': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ville',
            }),
            'tarif_journalier': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : 650',
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+33 6 12 34 56 78',
            }),
            'experience_annees': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': "Nombre d'années",
            }),
            'delai_reponse': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : ~4h, ~1 jour',
            }),
            'disponibilite': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : 2 sem., Immédiate',
            }),
            'langues': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : FR, EN',
            }),
        }
 
 
class ProfilInstitutionForm(forms.ModelForm):
    """Champs spécifiques au profil institution."""
 
    class Meta:
        model = Institution
        fields = [
            'nom_organisation',
            'description',
            'localisation_institution',
            'site_web',
            'secteur',
            'taille_effectif',
        ]
        widgets = {
            'nom_organisation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': "Nom de l'organisation",
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': "Présentez votre organisation...",
            }),
            'localisation_institution': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ville',
            }),
            'site_web': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://...',
            }),
            'secteur': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : Enseignement supérieur, E-santé',
            }),
            'taille_effectif': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : 500+ collaborateurs',
            }),
        }