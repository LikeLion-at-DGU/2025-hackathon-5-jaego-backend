from django.db import models
import string, random

def _generate_code(): 
    chars = string.ascii_uppercase + string.digits 
    code = ''.join(random.choices(chars, k=6)) 
    return code

class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirm', 'Confirm'),
        ('pickup', 'PickUp'),
        ('ready', 'Ready'),
        ('cancel', 'Cancel'),
    ]
    consumer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='reservations')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='reservations')
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reservation_code = models.CharField(
        default= _generate_code,
        max_length=6, 
        unique=True, 
        editable=False)

    #pending
    created_at = models.DateTimeField(auto_now_add=True)
    #confirm
    reserved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.id} / {self.reservation_code}] {self.consumer.email} - {self.product.name} ({self.status}) / 가게명 : {self.product.store.store_name}"
    
    def save(self, *args, **kwargs):
        if not self.reservation_code:
            while True:
                code = _generate_code()
                if not Reservation.objects.filter(reservation_code=code).exists():
                    self.reservation_code = code
                    break
        super().save(*args, **kwargs)

    

class ReservationCancelReason(models.Model):
    reservation = models.OneToOneField(
        'Reservation',
        on_delete=models.CASCADE,
        related_name='cancel_reason'
    )
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"[{self.id}] ({self.reservation.id}) - {self.reason[:30]}"

class Notification(models.Model):
    STATUS_CHOICES = [
        ('confirm', 'Confirm'),
        ('pickup', 'PickUp'),
        ('ready','Ready'),
        ('cancel', 'Cancel'),
    ]
    reservation = models.ForeignKey(
        'Reservation',
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    status = models.CharField(max_length = 20, choices=STATUS_CHOICES)
    is_read = models.BooleanField(default = False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"[{self.id}] 예약 : {self.reservation.id} / 상태 : {self.status} / ({'읽음' if self.is_read else '안읽음'})"