from datetime import timedelta, timezone
from django.db import models

class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('picked_up', 'Picked Up'),
        ('cancelled', 'Cancelled'),
    ]
    consumer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='reservations')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='reservations')
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    reserved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.consumer.email} - {self.product.name} ({self.status})"

    @property
    def is_expired(self):
        if not self.reserved_at:
            return False
        return timezone.now() > self.reserved_at + timedelta(minutes = 10)