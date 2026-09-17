from django import forms

from .models import Offre
from account.models import Institution


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
