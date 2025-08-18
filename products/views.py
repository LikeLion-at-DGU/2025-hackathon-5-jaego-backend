from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.db.models import Q
from math import radians, cos, sin, asin, sqrt

from accounts.permissions import IsSeller, IsConsumer
from stores.models import Store
from .models import Product, Wishlist, RecommendedKeyword
from .utils import get_keywords_from_gpt_or_cache
from .serializers import ProductReadSerializer, ProductCreateUpdateSerializer


def haversine(lon1, lat1, lon2, lat2):
    # 둘 사이 거리 계산
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return km


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductReadSerializer
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    # 액션 별로 상이한 권한 부여
    def get_permissions(self):
        if self.action in ["list", "retrieve", "all_products", "toggle_wishlist", "my_wishlist", "discounted_products"]:
            permission_classes = [IsAuthenticated]  # 로그인만 하면 소비자/판매자 모두 접근 가능
        else:
            permission_classes = [IsAuthenticated, IsSeller]  # 등록/수정/삭제는 판매자만
        return [perm() for perm in permission_classes]

    def get_queryset(self):
        if self.action == "retrieve":
            # 상세조회는 소비자/판매자 모두 접근 가능하도록 조건 완화
            return Product.objects.select_related("store", "category").all()

        if IsSeller().has_permission(self.request, self):
            return (
                Product.objects
                .select_related("store", "category")
                .filter(store__seller=self.request.user)
                .order_by("-id")
            )
        else:
            return (
                Product.objects
                .select_related("store", "category")
                .filter(is_active=True, store__is_open=True)
                .order_by("-id")
            )

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return ProductCreateUpdateSerializer
        return ProductReadSerializer

    def perform_create(self, serializer):
        try:
            store = Store.objects.get(seller=self.request.user)
        except Store.DoesNotExist:
            raise ValidationError(
                {"store": "현재 로그인한 판매자 계정으로 등록된 매장이 없습니다. 매장 가입을 먼저 완료하세요."}
            )
        serializer.save(store=store)

    def destroy(self, request, *args, **kwargs):
        # 판매자인데 매장이 아직 없는 경우
        if not Store.objects.filter(seller=request.user).exists():
            raise ValidationError({"store": "현재 로그인한 판매자 계정으로 등록된 매장이 없습니다."})

        instance = self.get_object()  # 내 가게 상품만 매칭
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # 소비자 위시리스트
    @action(
        detail=True,
        methods=["post"],
        url_path="wishlist",
        permission_classes=[IsAuthenticated, IsConsumer],  # 소비자만
    )
    def toggle_wishlist(self, request, pk=None):
        product = get_object_or_404(
            Product.objects.select_related("store", "category").filter(is_active=True),
            pk=pk
        )

        wl, created = Wishlist.objects.get_or_create(
            consumer=request.user,
            product=product,
        )
        if created:
            wishlisted = True
        else:
            wl.delete()
            wishlisted = False

        return Response(
            {"product_id": product.id, "wishlisted": wishlisted},
            status=status.HTTP_200_OK
        )

    # 소비자 위시리스트 목록 조회
    @action(
        detail=False,
        methods=["get"],
        url_path="wishlist",
        permission_classes=[IsAuthenticated, IsConsumer],
    )
    def my_wishlist(self, request):
        product_qs = (
            Product.objects
            .select_related("store", "category")
            .filter(wishlisted_by__consumer=request.user)
            .order_by("-id")
        )

        page = self.paginate_queryset(product_qs)
        if page is not None:
            serializer = ProductReadSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)

        serializer = ProductReadSerializer(product_qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 근처 가게 상품 목록 조회 (소비자 전용)
    @action(
        detail=False,
        methods=["get"],
        url_path="nearby",
        permission_classes=[IsAuthenticated, IsConsumer],
    )
    def all_products(self, request):
        try:
            lat = float(request.query_params.get("lat"))
            lng = float(request.query_params.get("lng"))
            radius = float(request.query_params.get("radius", 5))  # 기본 5km
        except (TypeError, ValueError):
            return Response(
                {"error": "lat, lng, radius 파라미터를 올바르게 입력하세요."},
                status=status.HTTP_400_BAD_REQUEST
            )

        search = request.query_params.get("search", "").strip()  # 검색어 추가

        # 오픈 상태인 가게만 필터링
        stores = Store.objects.filter(is_open=True)

        # 거리 필터링
        nearby_store_ids = []
        for store in stores:
            if store.latitude and store.longitude:
                dist = haversine(lng, lat, store.longitude, store.latitude)
                if dist <= radius:
                    nearby_store_ids.append(store.id)

        queryset = (
            Product.objects
            .select_related("store", "category")
            .filter(is_active=True, store__id__in=nearby_store_ids)
        )

        # 검색어: 상품명 + 가게명 둘 다 지원
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(store__name__icontains=search)
            )

        queryset = queryset.order_by("-id")

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ProductReadSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)

        serializer = ProductReadSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 특가 상품만 조회
    @action(
        detail=False,
        methods=["get"],
        url_path="discount", 
        permission_classes=[IsAuthenticated, IsConsumer],
    )
    def discounted_products(self, request):
        try:
            lat = float(request.query_params.get("lat"))
            lng = float(request.query_params.get("lng"))
            radius = float(request.query_params.get("radius", 5))  # 기본 5km
        except (TypeError, ValueError):
            return Response(
                {"error": "lat, lng, radius 파라미터를 올바르게 입력하세요."},
                status=status.HTTP_400_BAD_REQUEST
            )

        stores = Store.objects.filter(is_open=True)

        nearby_store_ids = []
        for store in stores:
            if store.latitude and store.longitude:
                dist = haversine(lng, lat, store.longitude, store.latitude)
                if dist <= radius:
                    nearby_store_ids.append(store.id)

        # 할인율 30% 초과 조건 추가
        queryset = (
            Product.objects
            .select_related("store", "category")
            .filter(
                is_active=True,
                store__id__in=nearby_store_ids,
                discount_rate__gte=30
            )
            .order_by("-id")
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ProductReadSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)

        serializer = ProductReadSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_path="wishlist",
        permission_classes=[IsAuthenticated, IsConsumer],
    )
    def toggle_wishlist(self, request, pk=None):
        product = get_object_or_404(
            Product.objects.select_related("store", "category").filter(is_active=True),
            pk=pk
        )

        wl, created = Wishlist.objects.get_or_create(
            consumer=request.user,
            product=product,
        )

        keywords = get_keywords_from_gpt_or_cache(product.name, product.category.name)

        if created:
            # 찜 추가 시 -> 점수 +1
            for kw in keywords:
                rk, _ = RecommendedKeyword.objects.get_or_create(
                    consumer=request.user,
                    keyword=kw,
                    defaults={"score": 0}
                )
                rk.score += 1
                rk.save(update_fields=["score", "updated_at"])
            wishlisted = True
        else:
            # 찜 삭제 시 -> 점수 -1 (최소 0)
            for kw in keywords:
                try:
                    rk = RecommendedKeyword.objects.get(
                        consumer=request.user,
                        keyword=kw
                    )
                    rk.score = max(0, rk.score - 1)
                    rk.save(update_fields=["score", "updated_at"])
                except RecommendedKeyword.DoesNotExist:
                    pass
            wl.delete()
            wishlisted = False

        return Response(
            {"product_id": product.id, "wishlisted": wishlisted},
            status=status.HTTP_200_OK
        )

