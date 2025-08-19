from math import radians, cos, sin, asin, sqrt

from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action

from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser

from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _

from django.shortcuts import get_object_or_404


from .models import Store
from .serializers import *

from accounts.permissions import IsSeller,IsConsumer

class StoreViewSet(mixins.ListModelMixin, 
                mixins.RetrieveModelMixin,
                viewsets.GenericViewSet):
    queryset = Store.objects.all()
    permission_classes = [IsAuthenticated, IsSeller, IsConsumer]
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
        if self.action in ["list", "retrieve","products"] :
            return [IsAuthenticated()]
        
        elif self.action in ["nearby"] :
            return [IsAuthenticated(), IsConsumer()]
        
        #signup, 영업시간 체크 -> 판매자만
        return [IsAuthenticated(),IsSeller()]

    ######### (0) 모든 상점 조회 (필터 포함) #########
    #GET /stores/
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

    ######### (1) 상점 오픈 / 마감 #########
    # POST /stores/{store_id}/is_open/
    @action(detail=False, methods=["patch"], url_path="is_open")
    def toggle_is_open(self, request, pk=None):
        try:
            store = Store.objects.get(seller = request.user)
        except Store.DoesNotExist:
            return Response({"detal" : "해당 사용자의 상점이 없습니다."})
        
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
        # 1) 이미 상점 존재 여부 확인
        store = Store.objects.filter(seller=request.user).first()
        if store:
            # 이미 존재하면 step1 다시 생성하지 않고 기존 정보 반환
            return Response({
                "detail": "이미 상점이 존재합니다.",
                "store": StoreSerializer(store).data
            }, status=status.HTTP_200_OK)

        # 2) 새로운 상점 생성
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        store = serializer.save(seller=request.user)
        return Response({
            "detail": "상점 Step1 생성 완료",
            "store": StoreSerializer(store).data
        }, status=status.HTTP_201_CREATED)
    
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
            "store": StoreSerializer(store).data
        }, status=status.HTTP_200_OK)

    ######### (3) store/nearby/ - 주변 영업 중 상점 조회 #########
    @action(detail=False, methods=["post"], url_path="signup/step2")
    def signup_step2(self, request, *args, **kwargs):
        """
        상점 등록 Step2: 파일 업로드
        이미 업로드된 경우 중복 방지
        """
        # 1) 현재 사용자의 상점 가져오기
        store = Store.objects.filter(seller=request.user).first()
        if not store:
            return Response({"detail": "Step1을 먼저 완료해야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 2) 이미 Step2 완료 여부 확인 (모든 파일이 존재하면 완료로 간주)
        if store.business_license and store.permit_doc and store.bank_copy:
            return Response({
                "detail": "Step2 파일이 이미 모두 업로드되어 있습니다.",
                "store": StoreSerializer(store).data
            }, status=status.HTTP_200_OK)

        # 3) Serializer로 파일 업데이트
        serializer = self.get_serializer(store, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        store = serializer.save()

        # 4) 업로드 확인
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

        # 5) 메시지 설정
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
            "store": StoreSerializer(store).data
        }, status=status.HTTP_200_OK)


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