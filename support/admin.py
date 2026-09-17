from django.contrib import admin
from .models import SupportTicket

# Register your models here.

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('titre', 'user', 'email', 'gestsup_ticket_id', 'statut', 'created_at')
    list_filter = ('statut', 'created_at')
    search_fields = ('titre', 'description', 'email', 'gestsup_ticket_id', 'user__username')
    readonly_fields = ('created_at', 'updated_at')