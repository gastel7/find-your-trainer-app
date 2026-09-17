from django.contrib import admin
from django.urls import path, include

from notifications.views import service_worker

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('account.urls')),
    path('', include('core.urls')),
    path('', include('offre.urls')),
    path('', include('formation.urls')),
    path('', include('chat.urls')),
    path('', include('candidature.urls')),
    path('', include('evaluation.urls')),
    path('', include('support.urls')),
    path('', include('notifications.urls')),
    path('sw.js', service_worker, name='service_worker'),
]