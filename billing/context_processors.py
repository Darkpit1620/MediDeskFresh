def can_manage_billing(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or not user.is_staff or not user.is_active:
        return {'can_manage_billing': False}
    return {'can_manage_billing': user.is_superuser or user.groups.filter(name='Billing').exists()}
