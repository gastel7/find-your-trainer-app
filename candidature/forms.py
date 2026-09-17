from django import forms
from .models import Candidature

class CandidatureForm(forms.ModelForm):
    class Meta:

        model = Candidature

        fields = ['message', 'cv']

        widgets = {
            'message': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': (
                        'Présentez votre profil '
                        'et expliquez votre motivation'
                    )
                }
            ),

            'cv': forms.FileInput(
                attrs={
                    'class': 'form-control'
                }
            )
        }