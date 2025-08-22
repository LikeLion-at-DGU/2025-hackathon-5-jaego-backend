import numpy as np
from products.models import Product
from django.conf import settings

EMB_DIR = settings.EMBEDDINGS_DIR

def load_item_vectors():
    path = EMB_DIR / "product_vectors.npy"
    if path.exists() and path.stat().st_size > 0:
        return np.load(path)
    # 파일 없거나 비어있으면 빈 배열
    return np.empty((0, 1536), dtype="float32")  # 임베딩 차원에 맞춰 1536 사용

def load_item_ids():
    path = EMB_DIR / "product_ids.npy"
    if path.exists() and path.stat().st_size > 0:
        return np.load(path)
    return np.array([], dtype=np.int64)

ITEM_VECS = load_item_vectors()
ITEM_IDS = load_item_ids()
IDX = {int(pid): i for i, pid in enumerate(ITEM_IDS)}  # 빈 배열이면 빈 dict

########################################################
# 사용자 벡터 계산
def user_vector_from_likes(user):
    liked = Product.objects.filter(
        wishlisted_by__consumer=user, is_active=True, stock__gt=0
    ).values_list("id", flat=True)
    liked = [pid for pid in liked if pid in IDX]
    if not liked:
        # ITEM_VECS가 비어있으면 차원 안전하게 1536으로 초기화
        return np.zeros(ITEM_VECS.shape[1] if ITEM_VECS.size else 1536, dtype="float32")

    vecs = np.stack([ITEM_VECS[IDX[pid]] for pid in liked])
    u = vecs.mean(axis=0)
    return (u / (np.linalg.norm(u) + 1e-8)).astype("float32")

# 추천 계산
def recommend_for_user(user, limit=20, user_top_keywords=None):
    u = user_vector_from_likes(user)
    if not np.any(u):
        return Product.objects.filter(is_active=True, stock__gt=0).order_by("-created_at")[:limit]

    sims = ITEM_VECS @ u if ITEM_VECS.size else np.array([])  # ITEM_VECS 없으면 빈 배열
    
    kw_boost = np.zeros_like(sims)
    if user_top_keywords and ITEM_IDS.size:
        prod_qs = Product.objects.filter(id__in=ITEM_IDS.tolist()).values("id", "keywords")
        kw_map = {row["id"]: row.get("keywords") or [] for row in prod_qs}
        for i, pid in enumerate(ITEM_IDS):
            overlap = len(set(kw_map.get(int(pid), [])) & set(user_top_keywords))
            kw_boost[i] = 0.05 * overlap

    score = 0.9 * sims + 0.1 * kw_boost
    top_idx = np.argsort(-score)[:limit*5] if score.size else np.array([], dtype=int)
    top_ids = ITEM_IDS[top_idx].tolist() if top_idx.size else []

    qs = Product.objects.filter(id__in=top_ids, is_active=True, stock__gt=0) if top_ids else Product.objects.none()
    id2rank = {pid: r for r, pid in enumerate(top_ids)}
    return sorted(qs, key=lambda p: id2rank[p.id])[:limit]
