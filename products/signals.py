from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Product, Wishlist

@receiver(post_save, sender=Product) # 물건 비활성화 될 시 연결된 찜 삭제
def remove_wishlist_if_inactive(sender, instance, **kwargs):
    if not instance.is_active:
        Wishlist.objects.filter(product=instance).delete()
