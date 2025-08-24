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

class Command(BaseCommand):
    help = "Build product embeddings using OpenAI"

    def handle(self, *args, **options):
        build_all_embeddings()
