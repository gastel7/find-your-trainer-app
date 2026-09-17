from django.contrib import admin
from .models import Formation, InscriptionFormation, Attestation

admin.site.register(Formation)
admin.site.register(InscriptionFormation)
admin.site.register(Attestation)
