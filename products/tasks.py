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


@shared_task
def daily_embedding_refresh():
    global ITEM_VECS, ITEM_IDS, IDX
    build_all_embeddings()

    ITEM_VECS = load_item_vectors()  
    ITEM_IDS  = load_item_ids()

    IDX = {int(pid): i for i, pid in enumerate(ITEM_IDS)}