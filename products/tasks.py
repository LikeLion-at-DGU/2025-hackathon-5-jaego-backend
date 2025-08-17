from celery import shared_task
from django.utils import timezone
from .models import Product

@shared_task
def deactivate_expired_products():
    now = timezone.now()
    expired_qs = Product.objects.filter(expiration_date__lt=now, is_active=True)

    count = expired_qs.update(is_active=False)

    return f"{count}개의 유통기한 지난 상품이 비활성화되었습니다."
