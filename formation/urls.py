from django.urls import path

from . import views

app_name = 'formation'

urlpatterns = [
    path('formations/', views.list_formations, name='formations_list'),
    path('nouvelle-formation/', views.add_formation, name='publier_formation'),
    path('formation/<int:formation_id>/delete/', views.delete_formation, name='supprimer_formation'),
    path('search-formateur/', views.search_formateur, name='search_formateur'),
    path('edit-formation/<int:formation_id>/', views.edit_formation, name='edit_formation'),
    path('formation/<int:formation_id>/', views.detail_formation, name='detail_formation'),
    path('formation/<int:formation_id>/inscription/', views.inscription_formation, name='inscription_formation'),
    path('formation/<int:formation_id>/desinscription/', views.desinscription_formation, name='desinscription_formation'),
    path('formation/<int:formation_id>/support/', views.telecharger_support, name='telecharger_support'),
    path('formation/<int:formation_id>/terminer/', views.marquer_formation_terminee, name='marquer_formation_terminee'),
    path('inscription/<int:inscription_id>/attestation/', views.generer_attestation, name='generer_attestation'),
]
