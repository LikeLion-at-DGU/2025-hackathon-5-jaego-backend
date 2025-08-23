from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Reservation
from .serializers import ReservationUpdateSerializer
import logging

logger = logging.getLogger(__name__)

@shared_task
def cancel_expired_reservations():
    # 로컬 시간(KST) 기준 now
    now = timezone.localtime(timezone.now())
    expire_time = now - timedelta(minutes=10)
    
    # 디버그용 로그
    for r in Reservation.objects.filter(status='pending'):
        created_at_local = timezone.localtime(r.created_at)
        logger.info(f"🤍 id: {r.id}, created_at: {created_at_local}, now: {now}, expire_time: {expire_time}")
    
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

        # 취소 사유 및 상태 변경
        update_data = {
            'status': 'cancel',
            'cancel_reason': '예약 요청이 10분 경과되어 자동 취소되었습니다.'
        }
        serializer = ReservationUpdateSerializer(
            instance=reservation,
            data=update_data,
            partial=True,
            context={'request': None}
        )
        if serializer.is_valid():
            serializer.save()

    return f"❤️ {expired.count()}개 예약 취소."
