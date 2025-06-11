from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Allows dictionary lookup in templates using a variable as the key.
    Usage: {{ my_dictionary|get_item:my_key_variable }}
    """
    return dictionary.get(key)
