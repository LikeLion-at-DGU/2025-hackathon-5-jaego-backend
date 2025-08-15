from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Reservation

@shared_task
def cancel_expired_reservations():
    now = timezone.now()
    expire_time = now - timedelta(minutes = 10)
    
    expired = Reservation.objects.filter(
        status='pending',
        created_at__lte= expire_time
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