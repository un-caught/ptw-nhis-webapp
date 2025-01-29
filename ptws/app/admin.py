from django.contrib import admin
from .models import *


# Register your models here.
admin.site.register(SafetyPrecaution)
admin.site.register(WorkLocationIsolation)
admin.site.register(PersonalSafety)
admin.site.register(Hazards)

