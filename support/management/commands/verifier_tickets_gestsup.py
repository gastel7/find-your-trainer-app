"""
À lancer périodiquement (cron / tâche planifiée), ex. toutes les 5 minutes :
    */5 * * * * cd /chemin/vers/le/projet && python manage.py verifier_tickets_gestsup

GestSup n'a pas de webhook sortant (confirmé par sa doc) : on est obligés
de "sonder" (polling) l'état des tickets encore ouverts pour détecter
une résolution et prévenir l'utilisateur (in-app + push).
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from notifications.services import notifier_utilisateur
from support.models import SupportTicket
from support.services import get_gestsup_ticket, GestSupAPIError, GestSupTicketIntrouvable

MOTS_CLES_RESOLU = ('résolu', 'resolu', 'resolved', 'fermé', 'ferme', 'closed', 'clos')


def _est_resolu(payload):
    """
    GestSup expose 'ticket_state_id' (numérique, propre à chaque instance)
    et parfois 'ticket_state_name' (texte). On vérifie les deux :
      - l'id, comparé à GESTSUP_RESOLVED_STATE_IDS (à configurer une fois,
        cf. commentaire dans settings.py)
      - le nom, si présent, en repérant des mots-clés usuels
    """
    state_id = payload.get('ticket_state_id')
    if state_id is not None and str(state_id) in settings.GESTSUP_RESOLVED_STATE_IDS:
        return True

    state_name = (payload.get('ticket_state_name') or '').strip().lower()
    if state_name and any(mot in state_name for mot in MOTS_CLES_RESOLU):
        return True

    return False


class Command(BaseCommand):
    help = "Vérifie l'état des demandes d'aide encore ouvertes auprès de GestSup et notifie l'utilisateur si résolu."

    def handle(self, *args, **options):
        tickets_ouverts = SupportTicket.objects.filter(
            statut=SupportTicket.STATUT_ENVOYE,
            gestsup_ticket_id__isnull=False,
        )

        if not tickets_ouverts.exists():
            self.stdout.write("Aucun ticket ouvert à vérifier.")
            return

        for ticket in tickets_ouverts:
            try:
                payload = get_gestsup_ticket(ticket.gestsup_ticket_id)
            except GestSupTicketIntrouvable as exc:
                # Le ticket n'existe plus côté GestSup (supprimé, base
                # réinitialisée...) : on arrête de le vérifier, mais on ne
                # dit surtout PAS "résolu" — ce serait un mensonge envers
                # l'utilisateur. On note juste 'introuvable' localement.
                ticket.statut = SupportTicket.STATUT_INTROUVABLE
                ticket.save(update_fields=['statut', 'updated_at'])
                self.stdout.write(self.style.WARNING(
                    f"Ticket #{ticket.gestsup_ticket_id} → introuvable dans GestSup ({exc}), suivi arrêté."
                ))
                continue
            except GestSupAPIError as exc:
                self.stderr.write(f"Ticket #{ticket.gestsup_ticket_id} : impossible de vérifier ({exc})")
                continue

            if _est_resolu(payload):
                ticket.statut = SupportTicket.STATUT_RESOLU
                ticket.save(update_fields=['statut', 'updated_at'])

                notifier_utilisateur(
                    ticket.user,
                    titre="Ta demande d'aide a été résolue",
                    message=f"« {ticket.titre} » a été traitée. Merci de ta patience !",
                    url='',
                )
                self.stdout.write(self.style.SUCCESS(
                    f"Ticket #{ticket.gestsup_ticket_id} → résolu, utilisateur {ticket.user} notifié."
                ))
            else:
                self.stdout.write(f"Ticket #{ticket.gestsup_ticket_id} → toujours ouvert.")