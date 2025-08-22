from celery import shared_task
from django.utils import timezone
from .models import Product
from .management.commands.build_embeddings import build_all_embeddings, build_embedding_for_product


@shared_task
def deactivate_expired_products():
    now = timezone.now()
    expired_qs = Product.objects.filter(expiration_date__lt=now, is_active=True)

    count = expired_qs.update(is_active=False)

    return f"{count}개의 유통기한 지난 상품이 비활성화되었습니다."

#####################################################################
#단일 상품 등록/수정 시 임베딩 생성
# @shared_task
# def create_embedding_for_product(product_id):
#     try:
#         product = Product.objects.get(id=product_id, is_active=True)
#         build_embedding_for_product(product)  # 개별 상품 임베딩 생성
#         # 임베딩 메모리도 즉시 갱신
#         from accounts.services.reco import ITEM_VECS, ITEM_IDS, IDX, load_item_vectors, load_item_ids
#         ITEM_VECS[:] = load_item_vectors()
#         ITEM_IDS[:] = load_item_ids()
#         IDX.clear()
#         IDX.update({int(pid): i for i, pid in enumerate(ITEM_IDS)})
#     except Product.DoesNotExist:
#         pass

@shared_task
def daily_embedding_refresh():
    build_all_embeddings()  # 전체 활성 상품 임베딩 재생성
    # 메모리도 갱신
    from accounts.services.reco import ITEM_VECS, ITEM_IDS, IDX, load_item_vectors, load_item_ids
    ITEM_VECS[:] = load_item_vectors()
    ITEM_IDS[:] = load_item_ids()
    IDX.clear()
    IDX.update({int(pid): i for i, pid in enumerate(ITEM_IDS)})
