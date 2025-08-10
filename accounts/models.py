from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    nickname = models.CharField(max_length=50, blank=True, null=True)  # 소비자 전용
    phone = models.CharField(max_length=20)
    is_seller = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class UserRecommendedKeyword(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommended_keywords')
    keyword = models.CharField(max_length=100)
    score = models.FloatField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.keyword} ({self.score})"


class Seller(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    category = models.ForeignKey('categories.Category', on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=100)
    opening_time = models.CharField(max_length=50)
    is_open = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    business_license = models.FileField(upload_to='licenses/')
    permit_doc = models.FileField(upload_to='permits/')
    bank_copy = models.FileField(upload_to='bank_copies/')

    def __str__(self):
        return self.name
