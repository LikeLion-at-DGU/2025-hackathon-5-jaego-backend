from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta

from .models import Reservation
from .serializers import ReservationSerializer, ReservationCreateSerializer

class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return ReservationCreateSerializer
        return ReservationSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_seller:
            return Reservation.objects.filter(product__seller=user)
        return Reservation.objects.filter(consumer=user)

    #예약 생성 [POST reservations/products/]
    def perform_create(self, serializer):
        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']
        
        #재고 차감
        if product.stock < quantity:
            raise ValueError("재고 부족")
        
        product.stok -= quantity
        if product.stock == 0 :
            product.is_active = False
        
        product.save()
        
        #예약 생성 + reserved_at 저장
        serializer.save(
            consumer = self.request.user,
            reserved_at = timezone.now(),
            status = 'pending'
        )
    
    #예약 목록 조회 [GET reservations/products/]
    def list(self, request, *args, **kwargs):
        # 목록 조회 시 자동 만료 처리
        for r in self.get_queryset():
            r.auto_cancel_if_expired()
        return super().list(request, *args, **kwargs)

    ############# (예약 상태) ################################
    #예약 수락 [PATCH reservations/{id}/confirm/]
    @action(detail=True, methods=['patch'])
    def confirm(self, request, pk=None):
        reservation = self.get_object()
        reservation.status = 'confirmed'
        reservation.save()
        return Response({"status": "confirmed"}, status=status.HTTP_200_OK)

    #예약 취소 [PATCH reservations/{id}/cancel/]
    @action(detail=True, methods=['patch'])
    def cancel(self, request, pk=None):
        reservation = self.get_object()
        reservation.status = 'cancelled'
        reservation.product.stock += reservation.quantity
        reservation.product.save()
        reservation.save()
        return Response({"status": "cancelled"}, status=status.HTTP_200_OK)

    #예약 픽업 [PATCH reservations/{id}/pickup/]
    @action(detail=True, methods=['patch'])
    def pickup(self, request, pk=None):
        reservation = self.get_object()
        reservation.status = 'picked_up'
        reservation.save()
        return Response({"status": "picked_up"}, status=status.HTTP_200_OK)

    ##########################################################