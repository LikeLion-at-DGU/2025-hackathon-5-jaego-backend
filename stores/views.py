from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from .models import Store
from .serializers import StoreStep1Serializer, StoreReadSerializer, StoreStep2Serializer
from django.shortcuts import get_object_or_404
from accounts.permissions import IsSeller

class StoreViewSet(viewsets.GenericViewSet):
    queryset = Store.objects.all()
    permission_classes = [IsAuthenticated, IsSeller]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_serializer_class(self):
        if self.action == "signup_step1":
            return StoreStep1Serializer
        elif self.action == "signup_step2":
            return StoreStep2Serializer
        return StoreReadSerializer

    @action(detail=True, methods=["patch"], url_path="is_open")
    def toggle_is_open(self, request, pk=None):
        store = get_object_or_404(Store, pk=pk, seller=request.user)

        # 현재 값 반전
        store.is_open = not store.is_open
        store.save(update_fields=["is_open"])

        return Response({
            "store_id": store.id,
            "is_open": store.is_open
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="signup/step1")
    def signup_step1(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        store = serializer.save(seller=request.user)  # 로그인한 판매자를 store의 seller로 설정
        data = StoreReadSerializer(store).data
        return Response({"store": data}, status=status.HTTP_201_CREATED)

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
