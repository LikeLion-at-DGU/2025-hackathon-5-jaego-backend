from django.shortcuts import render

from rest_framework import viewsets
from .models import Category
from .serializers import CategorySerializer

from rest_framework.permissions import AllowAny

class CategoryViewset(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny] #권한 없음
