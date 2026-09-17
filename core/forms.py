from django import forms

from .models import Offre, Formation
from account.models import Institution, Formateur


class OffreForm(forms.ModelForm):

    # Champ institution (visible seulement pour admin)
    institution = forms.ModelChoiceField(
        queryset=Institution.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    class Meta:
        model = Offre

        fields = [
            'institution',
            'titre',
            'description',
            'nb_max_de_candidatures',
            'type_offre',
            'statut',
            'competences',
            'localisation',
            'budget',
            'date_debut',
            'date_cloture',
        ]

        widgets = {
            'titre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre de l’offre'
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Description...',
                'rows': 5
            }),

            'type_offre': forms.Select(attrs={
                'class': 'form-control'
            }),

            'nb_max_de_candidatures': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre maximum de candidatures'
            }),

            'statut': forms.Select(attrs={
                'class': 'form-control'
            }),

            'competences': forms.SelectMultiple(attrs={
                'class': 'form-control'
            }),

            'localisation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Localisation'
            }),

            'duree': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 3 mois'
            }),

            'budget': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Budget'
            }),

            'date_debut': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                }
            ),

            'date_cloture': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                }
            ),
        }


# Formulaire de formation
class FormationForm(forms.ModelForm):
 
    # Champ formateur (visible seulement admin)
    formateur = forms.ModelChoiceField(
        queryset=Formateur.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
 
    def __init__(self, *args, formateur_principal=None, **kwargs):
        """
        formateur_principal : à passer depuis la vue quand l'utilisateur
        connecté est un 'formateur' (le champ 'formateur' n'étant pas
        soumis dans ce cas, on ne peut pas le déduire de cleaned_data).
        Pour un admin, on se base directement sur cleaned_data['formateur'].
        """
        self._formateur_principal_force = formateur_principal
        super().__init__(*args, **kwargs)
 
    class Meta:
        model = Formation
 
        fields = [
            'formateur',
            'titre',
            'description',
            'categorie',
            'niveau',
            'prix',
            'adresse',
            'co_intervenants',
            'competences',
            'date_debut',
            'date_cloture',
            'nb_places_max',  # 👈 NOUVEAU'
            'support_pdf',       # 👈 nouveau
        ]
 
        widgets = {
            'titre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre de la formation'
            }),
 
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Décrivez votre formation'
            }),
 
            'niveau': forms.Select(attrs={
                'class': 'form-control'
            }),
 
 
            'prix': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Prix'
            }),
 
            # Correction 1 : Utilise un simple Select pour la catégorie !
            'categorie': forms.Select(attrs={
                'class': 'form-control w-full rounded-lg border p-2.5'
            }),
 
            # Correction 2 : Ajoute un ID ou une classe spécifique pour Select2 sur les champs multiples
            # 'co_intervenants': forms.SelectMultiple(attrs={
            #     'class': 'select2-multiple w-full form-control',
            #     'id': 'select-intervenants',
            # }),
 
            'competences': forms.SelectMultiple(attrs={
                'class': 'select2-multiple w-full form-control',
                'id': 'select-competences',
            }),
 
 
            'adresse': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Le lieu de la formation'
            }),
 
 
            'date_debut': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                }
            ),
 
            'date_cloture': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                }
            ),
 
            'nb_places_max': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 20',
                'min': 1,
            }),
 
            'support_pdf': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'application/pdf',
            }),
        }
 
    def clean(self):
        cleaned_data = super().clean()
 
        co_intervenants = cleaned_data.get('co_intervenants')
        formateur_admin = cleaned_data.get('formateur')
 
        # Le formateur principal effectif, peu importe le rôle qui soumet :
        # admin (champ du form) > formateur connecté (forcé) > instance existante (édition)
        formateur_final = (
            formateur_admin
            or self._formateur_principal_force
            or getattr(self.instance, 'formateur', None)
        )
 
        if formateur_final and co_intervenants and formateur_final in co_intervenants:
            self.add_error(
                'co_intervenants',
                "Le formateur principal ne peut pas être également co-intervenant de sa propre formation."
            )
 
        return cleaned_data
 