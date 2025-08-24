from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


# ( 1 ) User + role -> 소비자 / 판매자 ( 이메일 중복 불허 )
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, role=None, **extra_fields):
        if not email:
            raise ValueError("이메일은 필수입니다.")
        if role not in ('consumer', 'seller'):
            raise ValueError("role은 'consumer' 또는 'seller' 중 하나여야 합니다.")
        email = self.normalize_email(email)
        user = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 'seller')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('role') != 'seller':
            raise ValueError("슈퍼유저는 반드시 판매자(seller)여야 합니다.")
        return self.create_user(email, password, **extra_fields)

# User 모델
class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('consumer', '소비자'),
        ('seller', '판매자'),
    )
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False) 
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['role', 'name']

    objects = UserManager()

    def __str__(self):
        return f"[{self.id}] {self.email} ({self.role})"

