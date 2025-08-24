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
# 유저 벡터 계산
def user_vector_from_likes(user, max_recent=3):
    liked_qs = Product.objects.filter(
        wishlisted_by__consumer=user, is_active=True, stock__gt=0
    ).order_by('-id')
    liked = [pid for pid in liked_qs.values_list("id", flat=True) if pid in IDX]

    if not liked:
        return np.zeros(ITEM_VECS.shape[1] if ITEM_VECS.size else 1536, dtype="float32")

    liked = liked[:max_recent]
    vecs = np.stack([ITEM_VECS[IDX[pid]] for pid in liked])
    weights = np.linspace(1.0, 0.5, len(liked))[:, None]
    u = (vecs * weights).sum(axis=0) / weights.sum()
    return (u / (np.linalg.norm(u) + 1e-8)).astype("float32")

# ------------------------
# 거리 계산 (haversine)
def haversine(lat1, lng1, lat2, lng2):
    R = 6371
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lng2 - lng1)
    a = np.sin(dphi/2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

# ------------------------------------------------
# 추천 계산
def recommend_for_user(
    user,
    limit=10,
    sim_threshold=0.6,
    user_lat=None,
    user_lng=None,
    max_distance_km=5.0,
    store_weight=0.3,
    category_weight=0.4,
    distance_weight=0.3
    ):
    
    u = user_vector_from_likes(user)
    if not np.any(u):
        return Product.objects.none()

    liked_qs = Product.objects.filter(
        wishlisted_by__consumer=user, is_active=True, stock__gt=0
    ).order_by('-id')
    liked_ids = list(liked_qs.values_list("id", flat=True))
    liked_cats = list(liked_qs.values_list("category_id", flat=True))
    liked_stores = list(liked_qs.values_list("store_id", flat=True))

    candidates = Product.objects.filter(is_active=True, stock__gt=0)
    candidate_ids = [pid for pid in candidates.values_list("id", flat=True) if pid in IDX]
    if not candidate_ids:
        return Product.objects.none()

    candidate_vecs = ITEM_VECS[[IDX[pid] for pid in candidate_ids]]
    candidates_map = candidates.in_bulk(candidate_ids)

    # 거리 계산 및 필터 + 거리 점수
    dist_score = np.zeros(len(candidate_ids), dtype=np.float32)
    if user_lat is not None and user_lng is not None:
        distances = np.array([
            haversine(user_lat, user_lng, float(candidates_map[pid].store.latitude), float(candidates_map[pid].store.longitude))
            for pid in candidate_ids
        ])
        valid_distance_idx = np.where(distances <= max_distance_km)[0]
        if valid_distance_idx.size == 0:
            return Product.objects.none()
        candidate_ids = [candidate_ids[i] for i in valid_distance_idx]
        candidate_vecs = candidate_vecs[valid_distance_idx]
        distances = distances[valid_distance_idx]
        dist_score = 1 / (1 + distances)

    sims = candidate_vecs @ u
    
    # 보너스 점수 ( 상점, 카테고리, 거리 )
    bonus = np.zeros_like(sims)

    for i, pid in enumerate(candidate_ids):
        p = candidates_map[pid]
        if p.store_id in liked_stores:
            bonus[i] += store_weight
        if p.category_id in liked_cats:
            bonus[i] += category_weight
    bonus += distance_weight * dist_score

    # 최종 점수
    score = sims + bonus
    
    
    valid_idx = np.where(score >= sim_threshold)[0]
    if valid_idx.size == 0:
        return Product.objects.none()

    final_ids = [candidate_ids[i] for i in valid_idx]
    final_scores = score[valid_idx]

    top_idx = np.argsort(-final_scores)[:limit]
    top_ids = [final_ids[i] for i in top_idx]

    qs = Product.objects.filter(id__in=top_ids)
    id2rank = {pid: r for r, pid in enumerate(top_ids)}
    return sorted(qs, key=lambda p: id2rank[p.id])
