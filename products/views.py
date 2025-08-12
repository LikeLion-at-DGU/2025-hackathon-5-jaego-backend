from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from accounts.permissions import IsSeller
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
