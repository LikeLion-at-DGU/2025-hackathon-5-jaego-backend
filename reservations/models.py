from django.db import models

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
    
    #pending
    created_at = models.DateTimeField(auto_now_add=True)
    #confirm
    reserved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.id}] {self.consumer.email} - {self.product.name} ({self.status}) / 가게명 : {self.product.store.store_name}"

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
        return f"[{self.id}] - ({self.reservation.id}){self.status}({'읽음' if self.is_read else '안읽음'})"