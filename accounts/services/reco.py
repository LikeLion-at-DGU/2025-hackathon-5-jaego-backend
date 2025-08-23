import numpy as np
from products.models import Product
from django.conf import settings

EMB_DIR = settings.EMBEDDINGS_DIR

def load_item_vectors():
    path = EMB_DIR / "product_vectors.npy"
    if path.exists() and path.stat().st_size > 0:
        return np.load(path)
    return np.empty((0, 1536), dtype="float32")

def load_item_ids():
    path = EMB_DIR / "product_ids.npy"
    if path.exists() and path.stat().st_size > 0:
        return np.load(path)
    return np.array([], dtype=np.int64)

ITEM_VECS = load_item_vectors()
ITEM_IDS = load_item_ids()
IDX = {int(pid): i for i, pid in enumerate(ITEM_IDS)}

# ------------------------------------------------
# 유저 벡터 계산 (최근 찜 + 가중 평균)
def user_vector_from_likes(user, max_recent=3):
    liked_qs = Product.objects.filter(
        wishlisted_by__consumer=user, is_active=True, stock__gt=0
    ).order_by('-id')
    liked = [pid for pid in liked_qs.values_list("id", flat=True) if pid in IDX]

    if not liked:
        return np.zeros(ITEM_VECS.shape[1] if ITEM_VECS.size else 1536, dtype="float32")

    liked = liked[:max_recent]
    vecs = np.stack([ITEM_VECS[IDX[pid]] for pid in liked])
    weights = np.linspace(1.0, 0.5, len(liked))[:, None]  # 최근 찜 가중치
    u = (vecs * weights).sum(axis=0) / weights.sum()
    return (u / (np.linalg.norm(u) + 1e-8)).astype("float32")

# ------------------------------------------------
# 추천 계산 (후보군 좁히기 + 키워드 가중 + 유사도 필터)
def recommend_for_user(user, limit=10, user_top_keywords=None, sim_threshold=0.5):
    u = user_vector_from_likes(user)
    if not np.any(u):
        return Product.objects.none()

    liked_qs = Product.objects.filter(
        wishlisted_by__consumer=user, is_active=True, stock__gt=0
    ).order_by('-id')
    liked = liked_qs[:5]  # 최근 찜 상품 5개만 후보군 기준
    liked_cats = liked.values_list("category_id", flat=True)
    liked_stores = liked.values_list("store_id", flat=True)

    # 후보군: 찜 상품과 동일 카테고리 + 상점
    candidates = Product.objects.filter(
        is_active=True, stock__gt=0,
        category_id__in=liked_cats,
        store_id__in=liked_stores
    )
    candidate_ids = [pid for pid in candidates.values_list("id", flat=True) if pid in IDX]
    if not candidate_ids:
        return Product.objects.none()

    candidate_vecs = ITEM_VECS[[IDX[pid] for pid in candidate_ids]]
    sims = candidate_vecs @ u

    # 키워드 가중치 강화
    kw_boost = np.zeros_like(sims)
    if user_top_keywords:
        prod_qs = Product.objects.filter(id__in=candidate_ids).values("id", "keywords")
        kw_map = {row["id"]: row.get("keywords") or [] for row in prod_qs}
        for i, pid in enumerate(candidate_ids):
            overlap = len(set(kw_map.get(int(pid), [])) & set(user_top_keywords))
            kw_boost[i] = 0.3 * overlap  # 키워드 영향력 강화

    score = 0.9 * sims + 0.1 * kw_boost

    # 유사도 임계값 적용
    valid_idx = np.where(score >= sim_threshold)[0]
    if valid_idx.size == 0:
        return Product.objects.none()

    final_ids = [candidate_ids[i] for i in valid_idx]
    final_scores = score[valid_idx]

    # 상위 limit 개 선택
    top_idx = np.argsort(-final_scores)[:limit]
    top_ids = [final_ids[i] for i in top_idx]

    qs = Product.objects.filter(id__in=top_ids)
    id2rank = {pid: r for r, pid in enumerate(top_ids)}
    return sorted(qs, key=lambda p: id2rank[p.id])
