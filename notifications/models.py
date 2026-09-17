from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    Notification in-app (cloche du header). Générique : n'importe quelle
    partie de l'app peut en créer une via notifications.services.notifier_utilisateur().
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    titre = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    url = models.CharField(max_length=500, blank=True, help_text="Lien vers lequel rediriger au clic (optionnel).")
    lue = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"{self.titre} → {self.user}"


class PushSubscription(models.Model):
    """
    Un abonnement Web Push par navigateur/appareil (un utilisateur peut en
    avoir plusieurs : téléphone + PC par exemple). Rempli côté JS via
    pushManager.subscribe(), transmis à save_push_subscription().
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Abonnement push"
        verbose_name_plural = "Abonnements push"

    def __str__(self):
        return f"Abonnement push de {self.user}"

    def to_subscription_info(self):
        """Format attendu par pywebpush.webpush()."""
        return {
            "endpoint": self.endpoint,
            "keys": {
                "p256dh": self.p256dh,
                "auth": self.auth,
            },
        }