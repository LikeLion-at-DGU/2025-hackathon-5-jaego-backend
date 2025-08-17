from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Reservation
import logging

logger = logging.getLogger(__name__)

@shared_task
def cancel_expired_reservations():
    now = timezone.now()
    expire_time = now - timedelta(minutes=10)
    
    # 디버그용 로그
    for r in Reservation.objects.filter(status='pending'):
        print(f"id: {r.id}, created_at: {r.created_at}, now: {now}, expire_time: {expire_time}")
        logger.info(f"id: {r.id}, created_at: {r.created_at}, now: {now}, expire_time: {expire_time}")
    
    expired = Reservation.objects.filter(
        status='pending',
        created_at__lte=expire_time
    )

    for reservation in expired:
        product = reservation.product
        
        # 재고 복구
        product.stock += reservation.quantity
        product.is_active = True
        product.save()

        # 상태 변경
        reservation.status = 'cancel'
        reservation.save()

    return f"{expired.count()} reservations cancelled."
