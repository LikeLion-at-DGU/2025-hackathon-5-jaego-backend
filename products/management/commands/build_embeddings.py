from django.core.management.base import BaseCommand
from django.conf import settings
import numpy as np
from openai import OpenAI
from products.models import Product
import os

def build_all_embeddings():
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    os.makedirs(settings.EMBEDDINGS_DIR, exist_ok=True)

    products = Product.objects.filter(is_active=True, stock__gt=0)
    if not products.exists():
        print("No active products found.")
        return

    ids, vecs = [], []
    for p in products:
        text = f"{p.name} {p.store.store_name} {getattr(p.category, 'name', '') or ''}"
        try:
            res = client.embeddings.create(model="text-embedding-3-small", input=text)
            vec = res.data[0].embedding
            ids.append(p.id)
            vecs.append(vec)
        except Exception as e:
            print(f"Failed for product {p.id}: {e}")

    if ids and vecs:
        np.save(settings.EMBEDDINGS_DIR / "product_ids.npy", np.array(ids, dtype=np.int64))
        np.save(settings.EMBEDDINGS_DIR / "product_vectors.npy", np.array(vecs, dtype="float32"))
        print(f"Saved {len(ids)} embeddings to {settings.EMBEDDINGS_DIR}")
    else:
        print("No embeddings were created. Check API key or product queryset.")


def build_embedding_for_product(product):
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    os.makedirs(settings.EMBEDDINGS_DIR, exist_ok=True)

    text = f"{product.name} {product.store.store_name} {getattr(product.category, 'name', '') or ''}"

    try:
        res = client.embeddings.create(model="text-embedding-3-small", input=text)
        vec = res.data[0].embedding

        # 기존 파일 읽기
        ids_path = settings.EMBEDDINGS_DIR / "product_ids.npy"
        vecs_path = settings.EMBEDDINGS_DIR / "product_vectors.npy"

        ids = np.load(ids_path) if ids_path.exists() else np.array([], dtype=np.int64)
        vecs = np.load(vecs_path) if vecs_path.exists() else np.empty((0, len(vec)), dtype="float32")

        # 이미 존재하면 덮어쓰기, 없으면 추가
        if product.id in ids:
            idx = np.where(ids == product.id)[0][0]
            vecs[idx] = vec
        else:
            ids = np.append(ids, product.id)
            vecs = np.vstack([vecs, vec]) if vecs.size else np.array([vec], dtype="float32")

        # 저장
        np.save(ids_path, ids)
        np.save(vecs_path, vecs)

    except Exception as e:
        print(f"Failed for product {product.id}: {e}")

class Command(BaseCommand):
    help = "Build product embeddings using OpenAI"

    def handle(self, *args, **options):
        build_all_embeddings()
