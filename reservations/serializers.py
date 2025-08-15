from datetime import timezone
from rest_framework import serializers
from .models import Reservation

class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = '__all__'
        read_only_fields = ['status', 'created_at', 'reserved_at']

class ReservationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ['product', 'quantity']

    def create(self, validated_data):
        request = self.context['request']
        product = validated_data['product']
        quantity = validated_data['quantity']

        # 재고 차감
        if product.stock < quantity:
            raise serializers.ValidationError("재고가 부족합니다.")

        product.stock -= quantity
        product.save()

        reservation = Reservation.objects.create(
            consumer=request.user,
            product=product,
            quantity=quantity,
            reserved_at=timezone.now()
        )
        return reservation
