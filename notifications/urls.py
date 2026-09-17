from django.urls import path

from . import views

app_name = 'notifications'

urlpatterns = [
    path('notifications/', views.liste_notifications, name='liste'),
    path('notifications/<int:notif_id>/lu/', views.marquer_lu, name='marquer_lu'),
    path('notifications/tout-lire/', views.marquer_tout_lu, name='marquer_tout_lu'),
    path('notifications/push/abonner/', views.save_push_subscription, name='save_push_subscription'),
    path('notifications/push/desabonner/', views.remove_push_subscription, name='remove_push_subscription'),
]