from django.urls import path
from django.conf.urls.static import static

from find_your_trainer import settings
from . import views, models


app_name = 'core'

urlpatterns  = [
    path("", views.index, name='index'),
    path("dashboard/", views.dashboard, name='dashboard'),
    path('search-competence/', views.search_competence, name='search_competence'),
]


if settings.DEBUG:
    urlpatterns+= static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
)
