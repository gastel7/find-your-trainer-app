from django.urls import path
from django.conf.urls.static import static

from find_your_trainer import settings
from . import views

app_name = 'evaluation'

urlpatterns = [
    path('evaluations/',views.evaluations_list,name='evaluations_list'),
    path('mes-evaluations/',views.mes_evaluations,name='mes_evaluations'),
    path('detail/<int:evaluation_id>/',views.detail_evaluation,name='detail_evaluation'),
    path('candidature/<int:candidature_id>/',views.evaluer_candidature,name='evaluer_candidature'),
    path('evaluer-formation/<int:formation_id>/',views.evaluer_formation,name='evaluer_formation'),
]

if settings.DEBUG:
    urlpatterns+= static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
)