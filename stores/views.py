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

class StoreViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Store.objects.all()
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_serializer_class(self):
        if self.action == "signup_step1":
            return StoreStep1Serializer
        elif self.action == "signup_step2":
            return StoreStep2Serializer
        return StoreSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve","products"] :
            return [IsAuthenticated()]
        elif self.action in ["nearby"] :
            return [IsAuthenticated(), IsConsumer()]
        return [IsAuthenticated(),IsSeller()]

    # 모든 상점 조회
    def list(self, request, *args, **kwargs):
        qs = self.queryset
        
        # 1) is_open 필터
        is_open = request.query_params.get("is_open")
        if is_open == "true":
            qs = qs.filter(is_open=True)
        elif is_open == "false":
            qs = qs.filter(is_open=False)

        serializer = self.get_serializer(qs, many =True)
        return Response(serializer.data)

    # 가게 오픈/마감 처리
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

    
    # 상점 등록 step1
    @action(detail=False, methods=["post"], url_path="signup/step1")
    def signup_step1(self, request, *args, **kwargs):
        # 1) 이미 상점 존재 여부 확인
        store = Store.objects.filter(seller=request.user).first()
        if store:
            # 존재할 경우
            return Response({
                "detail": "이미 상점이 존재합니다.",
                "store": StoreSerializer(store).data
            }, status=status.HTTP_200_OK)

        # 2) 없을 시, 새로운 상점 생성
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        store = serializer.save(seller=request.user)
        return Response({
            "detail": "상점 Step1 생성 완료",
            "store": StoreSerializer(store).data
        }, status=status.HTTP_201_CREATED)
    
    # 상점 등록 step2
    @action(detail=False, methods=["post"], url_path="signup/step2")
    def signup_step2(self, request, *args, **kwargs):
        # 1) 현재 사용자의 상점 가져오기
        store = Store.objects.filter(seller=request.user).first()
        if not store:
            return Response({"detail": "Step1을 먼저 완료해야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 2) Step2 완료 여부 확인 (모든 파일이 존재하면 완료로 간주)
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
