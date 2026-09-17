from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    """
    Reconstruit la query string actuelle (recherche, filtres...) en ne
    changeant que les paramètres passés en argument (typiquement 'page').

    Usage dans un template :
        <a href="?{% query_transform page=page_obj.next_page_number %}">
    """
    request = context['request']
    updated = request.GET.copy()
    for key, value in kwargs.items():
        updated[key] = value
    return updated.urlencode()


@register.simple_tag
def elided_page_range(page_obj, on_each_side=1, on_ends=1):
    """
    Wrapper autour de Paginator.get_elided_page_range (les templates
    Django ne peuvent pas appeler une méthode avec arguments via la
    notation par point). Retourne les numéros de page à afficher,
    avec Paginator.ELLIPSIS ('…') pour les trous.

    Usage :
        {% elided_page_range page_obj as page_range %}
        {% for num in page_range %}...{% endfor %}
    """
    return page_obj.paginator.get_elided_page_range(
        page_obj.number, on_each_side=on_each_side, on_ends=on_ends
    )