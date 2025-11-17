def elevation_context(request):
    """
    Context processor to provide elevation status to all templates.
    This allows templates to conditionally show admin features based on temporary elevation.
    """
    return {
        'is_elevated_admin': request.session.get('elevated_admin', False),
        'original_user_id': request.session.get('_original_user_id'),
    }
