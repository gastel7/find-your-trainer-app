from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('chat/', views.chat, name='chat_accueil'), # Sans ID
    path('chat/<int:user_id>/', views.chat, name='chat_room'),
    path('chat/upload/', views.upload_chat_file, name='chat_upload_file'),
]