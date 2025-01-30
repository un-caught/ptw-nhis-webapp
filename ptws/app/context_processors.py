from django.contrib.auth.models import Group
from app.models import PTWForm, NHISForm

def user_groups(request):
    # Ensure the user is authenticated before querying the database
    if request.user.is_authenticated:
        # Count of 'approved' PTWForms created by the logged-in user
        approved_count = PTWForm.objects.filter(status='approved', user=request.user).count()
        open_count = NHISForm.objects.filter(status='open', user=request.user).count()
        closed_count = NHISForm.objects.filter(status='closed', user=request.user).count()

        # Count of 'pending' or other similar statuses for the logged-in user
        pend_count = PTWForm.objects.filter(
            status__in=['awaiting_supervisor', 'pending', 'awaiting_manager'],
            user=request.user
        ).count()

        # Group checks
        is_supervisor = request.user.groups.filter(name="supervisor").exists()
        is_manager = request.user.groups.filter(name="manager").exists()
        is_staff = request.user.groups.filter(name="staff").exists()
        is_vendor = request.user.groups.filter(name="vendor").exists()
    else:
        # For unauthenticated users, return default values
        approved_count = 0
        open_count = 0
        closed_count = 0
        pend_count = 0
        is_staff = False
        is_vendor = False
        is_supervisor = False
        is_manager = False

    # Return the context dictionary
    return {
        'is_staff': is_staff,
        'is_vendor': is_vendor,
        'is_supervisor': is_supervisor,
        'is_manager': is_manager,
        'approved_count': approved_count,
        'pend_count': pend_count,
        'open_count': open_count,
        'closed_count': closed_count,
    }