from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def paginate(request, queryset_or_list, per_page=9, param='page'):
    """
    Pagine un queryset (ou une simple liste Python déjà réalisée) et
    retourne un objet Page Django, prêt à être mis dans le contexte
    (ex : {'page_obj': page_obj}).

    Le template n'a plus qu'à :
      - itérer sur page_obj (au lieu de la liste/queryset brute)
      - inclure 'core/partials/pagination.html' pour les liens de
        navigation (précédent/suivant/numéros de page), qui préservent
        automatiquement les autres paramètres GET (recherche, filtres...)
        via le tag {% query_transform %}.
    """
    paginator = Paginator(queryset_or_list, per_page)
    page_number = request.GET.get(param)

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return page_obj