from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Formateur, Institution, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Étend l'admin standard de Django (BaseUserAdmin) pour garder toute la
    gestion des mots de passe/permissions, en ajoutant nos propres champs
    (role, profile_picture, date_inscription).
    """
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff', 'date_inscription')
    list_filter = BaseUserAdmin.list_filter + ('role',)
    search_fields = ('username', 'email', 'first_name', 'last_name')
    readonly_fields = ('date_inscription',)
    ordering = ('-date_inscription',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profil Find Your Trainer', {
            'fields': ('role', 'profile_picture', 'date_inscription'),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Profil Find Your Trainer', {
            'fields': ('role', 'profile_picture'),
        }),
    )


@admin.register(Formateur)
class FormateurAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'titre_professionnel', 'localisation_formateur',
        'tarif_journalier', 'experience_annees', 'disponibilite', 'is_verified',
    )
    list_filter = ('is_verified', 'localisation_formateur', 'disponibilite')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'titre_professionnel', 'biographie')
    filter_horizontal = ('competences',)
    autocomplete_fields = ('user',)

    fieldsets = (
        ('Compte', {
            'fields': ('user', 'is_verified'),
        }),
        ('Profil public', {
            'fields': ('titre_professionnel', 'biographie', 'competences', 'localisation_formateur'),
        }),
        ('Tarification & disponibilité', {
            'fields': ('tarif_journalier', 'experience_annees', 'delai_reponse', 'disponibilite', 'langues'),
        }),
        ('Contact', {
            'fields': ('telephone',),
        }),
    )


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = (
        'nom_organisation', 'user', 'secteur', 'localisation_institution',
        'taille_effectif', 'is_verified',
    )
    list_filter = ('is_verified', 'secteur', 'localisation_institution')
    search_fields = ('nom_organisation', 'user__username', 'description', 'secteur')
    autocomplete_fields = ('user',)

    fieldsets = (
        ('Compte', {
            'fields': ('user', 'is_verified'),
        }),
        ('Profil public', {
            'fields': ('nom_organisation', 'description', 'localisation_institution', 'site_web'),
        }),
        ('Informations complémentaires', {
            'fields': ('secteur', 'taille_effectif'),
        }),
    )