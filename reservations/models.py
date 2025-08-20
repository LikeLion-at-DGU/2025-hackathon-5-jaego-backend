from datetime import timedelta, timezone
from django.db import models
from django.forms import ValidationError

class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirm', 'Confirm'),
        ('pickup', 'PickUp'),
        ('cancel', 'Cancel'),
    ]
    consumer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='reservations')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='reservations')
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    reserved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.consumer.email} - {self.product.name} ({self.status})"
    

class Notification(models.Model):
    STATUS_CHOICES = [
        ('confirm', 'Confirm'),
        ('pickup', 'PickUp'),
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
        return f"[{self.reservation.id}]{self.status}({'읽음' if self.is_read else '안읽음'})"