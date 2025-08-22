# products/management/commands/build_embeddings.py

from django.core.management.base import BaseCommand
from django.conf import settings
import numpy as np
from openai import OpenAI
from products.models import Product
import os

class Command(BaseCommand):
    help = "Build product embeddings using OpenAI"

    def handle(self, *args, **options):
        # OpenAI 클라이언트 초기화
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # EMB_DIR 존재 확인
        os.makedirs(settings.EMBEDDINGS_DIR, exist_ok=True)

        # 활성 상품 조회
        products = Product.objects.filter(is_active=True, stock__gt=0)
        if not products.exists():
            self.stdout.write(self.style.ERROR("No active products found."))
            return

        ids, vecs = [], []

        for p in products:
            text = f"{p.name} {getattr(p.category, 'name', '') or ''} {(p.description or '')[:120]}"
            try:
                res = client.embeddings.create(model="text-embedding-3-small", input=text)
                vec = res.data[0].embedding
                ids.append(p.id)
                vecs.append(vec)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Failed for product {p.id}: {e}"))

        if ids and vecs:
            np.save(settings.EMBEDDINGS_DIR / "product_ids.npy", np.array(ids, dtype=np.int64))
            np.save(settings.EMBEDDINGS_DIR / "product_vectors.npy", np.array(vecs, dtype="float32"))
            self.stdout.write(self.style.SUCCESS(f"Saved {len(ids)} embeddings to {settings.EMBEDDINGS_DIR}"))
        else:
            self.stdout.write(self.style.ERROR("No embeddings were created. Check API key or product queryset."))
