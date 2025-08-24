from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Product, Wishlist

import logging
logger = logging.getLogger(__name__)

# 물건 비활성화 되었을 시 연결된 찜 삭제 로직
@receiver(post_save, sender=Product) 
def remove_wishlist_if_inactive(sender, instance, **kwargs):
    if not instance.is_active:
        Wishlist.objects.filter(product=instance).delete()
