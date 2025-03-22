from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary safely.
    Returns None if the key is not found or the dictionary is None.
    """
    if dictionary is None:
        return None
    return dictionary.get(key) 