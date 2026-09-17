from django.urls import path
from . import views, models


app_name = 'account'

urlpatterns  = [
    # Les urls de connexion
    path("login/", views.log_in, name='log_in'),
    path("logup/", views.log_up, name='log_up'),
    path("logout/", views.log_out, name='log_out'),
    path("admin-login/", views.adminLogin, name='admin_login'),

    # Connexion avec Google (voir settings.py pour la config des identifiants)
    path("accounts/google/login/", views.google_login, name='google_login'),
    path("accounts/google/callback/", views.google_callback, name='google_callback'),

    # Les urls de la partie "App lorsque l'utilisateur n'est pas connecté"
    path('institutions-list/', views.list_institutions, name='institutions_list'),
    path('institutions/<int:pk>/', views.detail_institution, name='detail_institution'),
    path('formateurs-list/', views.list_formateurs, name='formateurs_list'),
    path('formateurs/<int:pk>/', views.detail_formateur, name='detail_formateur'),


    path('parametres/', views.parametres_profil, name='parametres_profil'),


]