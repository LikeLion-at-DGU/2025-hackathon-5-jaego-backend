from celery import shared_task
from django.utils import timezone
from .models import Product

from accounts.services.reco import ITEM_VECS, ITEM_IDS, IDX, load_item_vectors, load_item_ids
from .management.commands.build_embeddings import build_all_embeddings


@shared_task
def deactivate_expired_products():
    now = timezone.now()
    expired_qs = Product.objects.filter(expiration_date__lt=now, is_active=True)

    count = expired_qs.update(is_active=False)

    return f"{count}개의 유통기한 지난 상품이 비활성화되었습니다."

#####################################################################
@shared_task
def daily_embedding_refresh():
    build_all_embeddings()  # 전체 활성 상품 임베딩 재생성
    # 메모리 갱신
    ITEM_VECS_new = load_item_vectors()
    ITEM_IDS_new = load_item_ids()
    IDX.clear()
    IDX.update({int(pid): i for i, pid in enumerate(ITEM_IDS_new)})

    # 전역 변수 덮어쓰기
    ITEM_VECS[:] = ITEM_VECS_new  # numpy array라면 이렇게 가능
    ITEM_IDS[:] = ITEM_IDS_new