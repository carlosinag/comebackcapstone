from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using bracket notation."""
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def items(dictionary):
    """Get items from a dictionary."""
    if dictionary is None:
        return []
    return dictionary.items()

@register.filter
def clean_procedure_type(procedure_name):
    """Clean procedure type name by removing 'ultrasound' and extra spaces."""
    if not procedure_name:
        return ''
    return procedure_name.lower().replace('ultrasound', '').replace(' ', '').strip() 