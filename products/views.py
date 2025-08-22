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
from .models import Product, Wishlist
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


    # 근처 가게 상품 목록 조회 (소비자 전용)
    @action(
        detail=False,
        methods=["get"],
        url_path="nearby",
        permission_classes=[IsAuthenticated, IsConsumer],
    )
    def all_products(self, request):
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        radius = request.query_params.get("radius", 5) 
        
        try:
            lat = float(lat) if lat is not None else None
            lng = float(lng) if lng is not None else None
            radius = float(radius)
        except (TypeError, ValueError):
            return Response(
                {"error": "lat, lng, radius 파라미터를 올바르게 입력하세요."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 필터
        search = request.query_params.get("search", "").strip()  
        category_id = request.query_params.get("category")
        
        # 오픈 상태인 가게만 필터링
        stores = Store.objects.filter(is_open=True)

        # 기본 : 모든 store id
        nearby_store_ids = stores.values_list("id", flat = True)

        # lat/lng 있으면 반경 필터 
        if lat is not None and lng is not None:
            nearby_store_ids = []
            for store in stores:
                if store.latitude and store.longitude:
                    dist = haversine(lng, lat, store.longitude, store.latitude)
                    if dist <= radius:
                        nearby_store_ids.append(store.id)
            # 범위 내 가게가 없으면 빈 queryset이 되지 않도록
            if nearby_store_ids:
                stores = stores.filter(id__in=nearby_store_ids)
        # lat/lng가 없으면 stores 그대로 전체 범위 사용

        queryset = (
            Product.objects
            .select_related("store", "category")
            .filter(is_active=True, store__in=nearby_store_ids)
        )

        # 검색어: 상품명 + 가게명 둘 다 지원
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(store__name__icontains=search)
            )
            
        if category_id:
            queryset = queryset.filter(category_id = category_id)

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

    ####################################################33
    #찜 추가/ 삭제 (toggle)
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
        
        if not created:
            # 찜 삭제
            wl.delete()
            wishlisted = False
        else:
            # 찜 추가
            wishlisted = True

        return Response(
            {"product_id": product.id, "wishlisted": wishlisted},
            status=status.HTTP_200_OK
        )
    
    #########################################

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

