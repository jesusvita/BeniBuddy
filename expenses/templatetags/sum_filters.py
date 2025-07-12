from django import template

register = template.Library()

@register.filter
def sum_attr(expense_list, attr_name):
    """
    Sums the specified attribute from a list of model objects.
    Usage: {{ my_list|sum_attr:"amount" }}
    """
    total = 0
    for obj in expense_list:
        value = getattr(obj, attr_name, 0)
        if value is not None:
            total += value
    return total
