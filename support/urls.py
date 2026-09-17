from django.urls import path

from . import views

app_name = 'support'

urlpatterns = [
    path('aide/nouvelle-demande/', views.creer_demande_aide, name='creer_demande_aide'),
]