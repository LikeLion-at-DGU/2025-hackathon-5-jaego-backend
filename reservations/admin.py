from django.contrib import admin
from .models import Reservation, ReservationCancelReason, Notification

admin.site.register(Reservation)
admin.site.register(ReservationCancelReason)
admin.site.register(Notification)
