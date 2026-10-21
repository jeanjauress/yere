from django import template

register = template.Library()


@register.filter
def xof(value):
    """Formate un montant entier en francs CFA : 12500 -> « 12 500 FCFA »."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value
    return f"{value:,}".replace(",", " ") + " FCFA"


@register.filter
def stars(value):
    try:
        n = round(float(value or 0))
    except (TypeError, ValueError):
        n = 0
    return "★" * n + "☆" * (5 - n)


@register.simple_tag(takes_context=True)
def page_url(context, page_number):
    qs = context.get("querystring", "")
    return f"?{qs + '&' if qs else ''}page={page_number}"


@register.filter
def bs(field):
    """Rend un champ de formulaire avec les classes Bootstrap adaptées à son widget."""
    widget = field.field.widget
    name = widget.__class__.__name__
    if name in ("CheckboxInput",):
        css = "form-check-input"
    elif name in ("Select", "SelectMultiple"):
        css = "form-select"
    elif name in ("RadioSelect", "CheckboxSelectMultiple"):
        return field
    else:
        css = "form-control"
    if field.errors:
        css += " is-invalid"
    existing = widget.attrs.get("class", "")
    return field.as_widget(attrs={"class": f"{existing} {css}".strip()})
