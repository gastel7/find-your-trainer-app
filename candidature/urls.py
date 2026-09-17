from django.urls import path
from django.conf.urls.static import static

from find_your_trainer import settings
from . import views, models

# ==========================
# CANDIDATURES
# ==========================

app_name = 'candidature'

urlpatterns  = [
    path('postuler/<int:offre_id>/', views.postuler_offre, name='postuler_offre'),
    path('mes-candidatures/', views.mes_candidatures, name='mes_candidatures'),
    path('candidatures-recues/', views.candidatures_recues, name='candidatures_recues'),
    path('candidature/<int:candidature_id>/accepter/', views.accepter_candidature, name='accepter_candidature'),
    path('candidature/<int:candidature_id>/refuser/', views.refuser_candidature, name='refuser_candidature'),
    path('candidature/<int:candidature_id>/retirer/', views.retirer_candidature,name='retirer_candidature'),
    path('candidatures/exporter/', views.exporter_candidatures_csv, name='exporter_candidatures_csv'),
    path('candidatures/exporter/pdf/', views.exporter_candidatures_pdf, name='exporter_candidatures_pdf'),
]