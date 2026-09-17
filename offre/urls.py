from django.urls import path

from . import views

app_name = 'offre'

urlpatterns = [
    path('list-offres/', views.list_offres, name='offres_list'),
    path('add-offre/', views.ajouter_offre, name='ajouter_offre'),
    path('delete-offre/<int:offre_id>/', views.supprimer_offre, name='supprimer_offre'),
    path('edit-offre/<int:offre_id>/', views.edit_offre, name='edit_offre'),
    path('search-institution/', views.search_institution, name='search_institution'),
]
