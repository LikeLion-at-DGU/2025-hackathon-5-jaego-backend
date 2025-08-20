from django.utils import timezone
from rest_framework import serializers
from .models import Reservation, Notification

class ReservationSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True) 
    consumer = serializers.SerializerMethodField()
    reserved_at = serializers.DateTimeField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)
    class Meta:
        model = Reservation
        fields = '__all__'
        read_only_fields = ['status', 'created_at', 'reserved_at']
        
    def get_consumer(self, obj):
        user = obj.consumer
        return {
            'id': user.id,
            'email': user.email,
            'phone': getattr(user, 'phone', '')
        }

class ReservationCreateSerializer(serializers.ModelSerializer):
    consumer = serializers.SerializerMethodField()
    reserved_at = serializers.DateTimeField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)
    
    class Meta:
        model = Reservation
        fields = '__all__'
        
    def get_consumer(self, obj):
        user = obj.consumer
        return {
            'id': user.id,
            'email': user.email,
            'phone': getattr(user, 'phone', '')
        }
    
    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        
        product = validated_data['product']
        quantity = validated_data['quantity']
        
        # 재고 차감 및 상품 상태 변경
        if product.stock < quantity:
            raise serializers.ValidationError("재고가 부족합니다.")
        
        product.stock -= quantity
        
        if product.stock == 0:
            product.is_active = False
        product.save()

        # 예약 생성
        reservation = Reservation.objects.create(
            consumer=user,
            product=product,
            quantity=quantity,
            status='pending'
        )
        return reservation

from rest_framework import serializers
from .models import Reservation

class ReservationUpdateSerializer(serializers.ModelSerializer):
    consumer = serializers.SerializerMethodField()
    class Meta:
        model = Reservation
        fields = '__all__'
        
    def get_consumer(self, obj):
        user = obj.consumer
        return {
            'id': user.id,
            'email': user.email,
            'phone': getattr(user, 'phone', '')
        }

    def validate(self, attrs):
        reservation = self.instance
        new_status = attrs.get('status')

        # 취소된 예약은 변경 불가
        if reservation.status == 'cancel':
            raise serializers.ValidationError("이미 취소된 예약은 상태를 변경할 수 없습니다.")

        # 상태 변경 유효성 검사
        valid_transitions = {
            'pending': ['confirm', 'cancel'],
            'confirm': ['pickup', 'cancel'], #픽업만 가능하게?
            'pickup': [],
            'cancel': []
        }
        if new_status not in valid_transitions[reservation.status]:
            raise serializers.ValidationError(f"{reservation.status} → {new_status} 변경은 허용되지 않습니다.")

        return attrs

    def update(self, instance, validated_data):
        new_status = validated_data['status']

        # confirm → reserved_at 기록
        if new_status == 'confirm':
            from django.utils import timezone
            instance.reserved_at = timezone.now()

        # cancel → 재고 복구
        if new_status == 'cancel':
            product = instance.product
            product.stock += instance.quantity
            product.is_active = True
            product.save()

        #상태 변경
        instance.status = new_status
        instance.save()
        
        # Notification 생성
        Notification.objects.get_or_create(
            reservation=instance,
            status=new_status,
            defaults={'is_read': False}
        )
        
        return instance

#########################################################
# 알람
class NotificationSerializer(serializers.ModelSerializer):
    reservation_id = serializers.IntegerField(source="reservation.id", read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "reservation_id", "status", "is_read", "created_at", "updated_at"]
