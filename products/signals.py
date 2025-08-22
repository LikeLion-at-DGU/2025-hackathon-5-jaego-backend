from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Product, Wishlist
# from .tasks import create_embedding_for_product

import logging
logger = logging.getLogger(__name__)

@receiver(post_save, sender=Product) # 물건 비활성화 될 시 연결된 찜 삭제
def remove_wishlist_if_inactive(sender, instance, **kwargs):
    if not instance.is_active:
        Wishlist.objects.filter(product=instance).delete()

# @receiver(post_save, sender=Product)
# def handle_product_save(sender, instance, created, **kwargs):
#     logger.info(f"handle_product_save 호출됨 | product_id={instance.id}, created={created}, is_active={instance.is_active}")
#     print(f"[DEBUG] handle_product_save 호출됨: {instance.id}, created={created}, active={instance.is_active}")
    
#     if instance.is_active:
#         create_embedding_for_product.delay(instance.id)