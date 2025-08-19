from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsSeller, IsConsumer

from django.utils.dateparse import parse_date

from .models import Reservation, Notification
from .serializers import ReservationSerializer, ReservationCreateSerializer, ReservationUpdateSerializer, NotificationSerializer

class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return ReservationCreateSerializer
        return ReservationSerializer
    
    ## 권한 부여
    def get_permissions(self):
        #목록 -> 로그인 상태
        if self.action in ["list"] :
            return [IsAuthenticated()]
        
        #생성 / 목록 -> 로그인 상태
        elif self.action in ["create"] :
            return [IsAuthenticated(), IsConsumer()]
        
        #status 변경 -> 판매자만
        return [IsAuthenticated(), IsSeller()]

    def get_queryset(self):
        user = self.request.user
        qs = Reservation.objects.all()
        
        if user.role == 'seller':
            qs = qs.filter(product__store__seller=user)
        else : 
            qs = qs.filter(consumer=user)

        #(1) 날짜
        start_date_str = self.request.query_params.get('start_date')
        end_date_str = self.request.query_params.get('end_date')

        if start_date_str:
            start_date = parse_date(start_date_str)
            if start_date:
                qs = qs.filter(created_at__date__gte=start_date)
        if end_date_str:
            end_date = parse_date(end_date_str)
            if end_date:
                qs = qs.filter(created_at__date__lte=end_date)

        #(2) status
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
            
        #(3) product_id
        product_id_param = self.request.query_params.get('product_id')
        if product_id_param:
            qs = qs.filter(product__id=product_id_param)
        
        
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 예약 상태 변경 권한 검사
    def _check_seller_owns_reservation(self, reservation):
        user = self.request.user
        if user.role != 'seller' or reservation.product.store.seller != user:
            return False
        return True
    
    ############# (예약 상태) ################################
    def _update_status(self, request, pk, new_status):
        reservation = self.get_object()
        if not self._check_seller_owns_reservation(reservation):
            return Response({"detail": "권한 없음"}, status=status.HTTP_403_FORBIDDEN)

        serializer = ReservationUpdateSerializer(
            reservation, 
            data={'status': new_status}, 
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
    #예약 수락 [PATCH reservations/{id}/confirm/]
    @action(detail=True, methods=['patch'])
    def confirm(self, request, pk=None):
        return self._update_status(request, pk, 'confirm')

    #예약 취소 [PATCH reservations/{id}/cancel/]
    @action(detail=True, methods=['patch'])
    def cancel(self, request, pk=None):
        return self._update_status(request, pk, 'cancel')

    #예약 픽업 [PATCH reservations/{id}/pickup/]
    @action(detail=True, methods=['patch'])
    def pickup(self, request, pk=None):
        return self._update_status(request, pk, 'pickup')

    ##########################################################

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, IsConsumer]

    def get_queryset(self):
        # 로그인한 사용자 본인의 reservation 알림만 보이도록
        user = self.request.user
        return Notification.objects.filter(reservation__consumer=user)
    
    ## 읽음 처리 API
    @action(detail=True, methods=['patch'])
    def read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({"detail": "읽음 처리 완료"})