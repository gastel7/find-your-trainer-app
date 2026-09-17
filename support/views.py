from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from notifications.services import notifier_utilisateur
from .models import SupportTicket
from .services import create_gestsup_ticket, GestSupAPIError

User = get_user_model()


@login_required
@require_POST
def creer_demande_aide(request):
    """
    Reçoit la soumission du modal "Besoin d'aide" (AJAX, JSON en retour —
    même convention que le modal d'évaluation : {'ok': bool, 'message'/'error': str}).
    """
    titre = (request.POST.get('titre') or '').strip()
    description = (request.POST.get('description') or '').strip()
    email = (request.POST.get('email') or request.user.email or '').strip()

    if not titre or not description:
        return JsonResponse({'ok': False, 'error': "Merci de renseigner un titre et une description."})

    if not email:
        return JsonResponse({'ok': False, 'error': "Une adresse email est nécessaire pour suivre ta demande."})

    ticket = SupportTicket.objects.create(
        user=request.user,
        titre=titre,
        description=description,
        email=email,
    )

    # L'API GestSup n'a pas de paramètre pour transmettre un nom/prénom :
    # on l'ajoute donc directement dans le texte envoyé, pour que le
    # technicien sache tout de suite qui demande quoi.
    nom_complet = request.user.get_full_name().strip()
    identite = f"{nom_complet} ({request.user.username})" if nom_complet else request.user.username
    description_gestsup = f"Demande de : {identite}\n\n{description}"

    try:
        payload = create_gestsup_ticket(titre, description_gestsup, email)
    except GestSupAPIError as exc:
        ticket.statut = SupportTicket.STATUT_ERREUR
        ticket.save(update_fields=['statut', 'updated_at'])
        return JsonResponse({
            'ok': False,
            'error': f"Ta demande n'a pas pu être transmise ({exc}). Réessaie dans un instant.",
        })

    ticket.gestsup_ticket_id = payload.get('ticket_id')
    ticket.gestsup_url = payload.get('ticket_url', '')
    ticket.save(update_fields=['gestsup_ticket_id', 'gestsup_url', 'updated_at'])

    for admin in User.objects.filter(role='admin'):
        notifier_utilisateur(
            admin,
            titre="Nouveau signalement",
            message=f"{identite} a signalé un problème : « {titre} ». Rendez-vous dans GestSup pour le traiter.",
            url=ticket.gestsup_url or '',
        )

    return JsonResponse({
        'ok': True,
        'message': f"Ta demande a bien été envoyée (ticket #{ticket.gestsup_ticket_id}). "
                   "Tu seras notifié dès qu'elle sera traitée.",
    })