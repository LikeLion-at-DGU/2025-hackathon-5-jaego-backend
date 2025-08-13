from math import radians, cos, sin, asin, sqrt

from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action

from rest_framework.permissions import IsAuthenticated, BasePermission, AllowAny
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser

from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _

from django.shortcuts import get_object_or_404
from django.db.models import Exists, OuterRef


from .models import Store
from .serializers import *

from accounts.permissions import IsSeller

class StoreViewSet(mixins.ListModelMixin, 
                mixins.RetrieveModelMixin,
                viewsets.GenericViewSet):
    queryset = Store.objects.all()
    permission_classes = [IsAuthenticated, IsSeller]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    ## serializer 설정
    def get_serializer_class(self):
        if self.action == "signup_step1":
            return StoreStep1Serializer
        
        elif self.action == "signup_step2":
            return StoreStep2Serializer
        
        return StoreSerializer
    
    ## 권한 부여
    def get_permissions(self):
        #조회 / 상세 / 주변 / 상품조회 / 요약
        if self.action in ["list", "retrieve", "nearby"] :
            return [AllowAny()]
        
        #signup, 영업시간 체크 -> 판매자만
        return [IsAuthenticated(),IsSeller()]

    ######### (0) 모든 상점 조회 (필터 포함) #########
    def list(self, request, *args, **kwargs):
        qs = self.queryset
        
        #1) is_open 필터
        is_open = request.query_params.get("is_open")
        if is_open in [ True ]:
            qs = qs.filter(is_open = True)
        elif is_open in [ False ]:
            qs = qs.filter(is_open = False)
            
        serializer = self.get_serializer(qs, many =True)
        return Response(serializer.data)

        
        #위치 기반 필터링
        #lat = request.query_params.get('latitude')
        #lng = request.query_params.get('longitude')
        #radius_km = request.query_params.get('radius')
        
        # 카테고리 필터링 (category_id)
        #⚠️ 수정 필요 ... 카테고리를 적용하면 해당 카테고리 상품을 팔고 있는 상점이 뜨게?
        #category_id = request.query_params.get('category_id')

        #if lat and lng and radius_km:
        #    try:
        #        lat = float(lat)
        #        lng = float(lng)
        #        radius_km = float(radius_km)
        #    except ValueError:
        #        return Response({"detail": "latitude, longitude, radius는 숫자여야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        #    # 거리계산용 함수
        #    def haversine(lat1, lon1, lat2, lon2):
        #        R = 6371
        #        dlat = radians(lat2 - lat1)
        #        dlon = radians(lon2 - lon1)
        #        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        #        c = 2 * asin(sqrt(a))
        #        return R * c

        #    stores_in_radius = []
        #    for store in qs:
        #        dist = haversine(lat, lng, float(store.latitude), float(store.longitude))
        #        if dist <= radius_km:
        #            stores_in_radius.append(store.id)
        #    qs = qs.filter(id__in=stores_in_radius)

        #if category_id:
        #    qs = qs.filter(
        #        Exists(
        #            Product.objects.filter(store=OuterRef('pk'), category_id=category_id)
        #        )
        #    )

        #serializer = StoreSerializer(qs, many=True)
        #return Response(serializer.data)
    
    
    ######### (1) 상점 오픈 / 마감 #########
    @action(detail=True, methods=["patch"], url_path="is_open")
    def toggle_is_open(self, request, pk=None):
        store = get_object_or_404(Store, pk=pk, seller=request.user)

        # 현재 값 반전
        store.is_open = not store.is_open
        store.save(update_fields=["is_open"])

        return Response({
            "store_id": store.id,
            "name" : store.store_name,
            "is_open": store.is_open
        }, status=status.HTTP_200_OK)

    
    ######### (2-1) 상점 등록 1 #########
    @action(detail=False, methods=["post"], url_path="signup/step1")
    def signup_step1(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        store = serializer.save(seller=request.user)  # 로그인한 판매자를 store의 seller로 설정
        data = StoreSerializer(store).data
        return Response({"store": data}, status=status.HTTP_201_CREATED)

    ######### (2-2) 상점 등록 2 #########
    @action(detail=False, methods=["post"], url_path="signup/step2")
    def signup_step2(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        store = serializer.save()

        # 각 파일이 실제로 저장되었는지 여부 확인
        def file_info(f):
            if not f:
                return {"uploaded": False}
            try:
                url = request.build_absolute_uri(f.url)
            except Exception:
                url = None
            return {"uploaded": True}

        uploads = {
            "business_license": file_info(store.business_license),
            "permit_doc":       file_info(store.permit_doc),
            "bank_copy":        file_info(store.bank_copy),
        }

        # 업로드 확인 메세지 출력
        success_all = all(v["uploaded"] for v in uploads.values())
        if success_all:
            message = "3개 파일이 모두 업로드 됨."
        else:
            missing = [k for k, v in uploads.items() if not v["uploaded"]]
            pretty = ", ".join({
                "business_license": "사업자 등록증",
                "permit_doc": "영업 신고증",
                "bank_copy": "통장 사본"
            }[k] for k in missing)
            message = f"{pretty} 업로드가 누락됨"

        return Response({
            "message": message,
            "uploads": uploads,
            "store": StoreReadSerializer(store).data
        }, status=status.HTTP_200_OK)

    ######### (3) store/nearby/ - 주변 영업 중 상점 조회 #########
    @action(detail=False, methods=['get'], url_path='nearby', permission_classes=[AllowAny])
    def nearby(self, request):
        try:
            lat = float(request.query_params.get('lat'))
            lng = float(request.query_params.get('lng'))
            radius_km = float(request.query_params.get('radius', 5))
        except (TypeError, ValueError):
            return Response({"detail": "latitude, longitude는 필수 float 파라미터이며 radius는 선택 파라미터입니다."},
                            status=status.HTTP_400_BAD_REQUEST)

        def haversine(lat1, lon1, lat2, lon2):
            R = 6371
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
            c = 2 * asin(sqrt(a))
            return R * c

        stores = []
        for store in Store.objects.filter(is_open=True):
            dist = haversine(lat, lng, float(store.latitude), float(store.longitude))
            if dist <= radius_km:
                stores.append(store)

        serializer = StoreSerializer(stores, many=True)
        return Response(serializer.data)

    ######### (4) stores/{store_id}/products/ - 상점 내 상품 목록 조회 #########
    @action(detail=True, methods=['get'], url_path='products', permission_classes=[AllowAny])
    def products(self, request, pk=None):
        from products.models import Product
        from products.serializers import ProductReadSerializer
        
        store = get_object_or_404(Store, pk=pk)
        is_active = request.query_params.get('is_active')
        products = Product.objects.filter(store=store)
        if is_active is not None:
            if is_active.lower() in ['true', '1']:
                products = products.filter(is_active=True)
            elif is_active.lower() in ['false', '0']:
                products = products.filter(is_active=False)
        serializer = ProductReadSerializer(products, many=True)
        return Response(serializer.data)

    ######### (5) stores/{store_id}/products/summary/ - 상품 간략 목록 #########
    #@action(detail=True, methods=['get'], url_path='products/summary', permission_classes=[AllowAny])
    #def products_summary(self, request, pk=None):
    #    from products.models import Product
    #    from products.serializers import ProductReadSerializer
    #    
    #    store = get_object_or_404(Store, pk=pk)
    #    products = Product.objects.filter(store=store, is_active=True)
    #    serializer = ProductSummarySerializer(products, many=True)
    #    return Response(serializer.data)