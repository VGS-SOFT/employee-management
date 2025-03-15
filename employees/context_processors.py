from .views import get_notification_context

def notifications(request):
    if request.user.is_authenticated:
        return get_notification_context(request)
    return {} 