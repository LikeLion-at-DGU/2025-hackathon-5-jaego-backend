from django.db import models
from accounts.models import User

# Create your models here.
# 상점 (판매자 1:1 관계)
class Store(models.Model):
    seller = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='store',
    )
    store_name = models.CharField(max_length=100)
    opening_time = models.CharField(max_length=50)
    is_open = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=200)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    business_license = models.FileField(upload_to='licenses/', blank=True, null=True)
    permit_doc = models.FileField(upload_to='permits/', blank=True, null=True)
    bank_copy = models.FileField(upload_to='bank_copies/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)