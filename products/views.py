from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from accounts.permissions import IsSeller
from rest_framework.response import Response
from stores.models import Store
from rest_framework.exceptions import ValidationError
from .models import Product
from .serializers import ProductReadSerializer, ProductCreateUpdateSerializer

class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsSeller]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_queryset(self):
        # 판매자 매장의 상품만 보이도록 함
        return (
            Product.objects
            .select_related("store", "category")
            .filter(store__seller=self.request.user)
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
            raise ValidationError({"store": "현재 로그인한 판매자 계정으로 등록된 매장이 없습니다. 매장 가입을 먼저 완료하세요."})
        serializer.save(store=store)

    def destroy(self, request, *args, **kwargs):
        # 판매자인데 매장이 아직 없는 경우
        if not Store.objects.filter(seller=request.user).exists():
            raise ValidationError({"store": "현재 로그인한 판매자 계정으로 등록된 매장이 없습니다."})

        instance = self.get_object()  # 내 가게 상품만 매칭
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)