from rest_framework import serializers
from decimal import Decimal, InvalidOperation
from .models import Store
from accounts.models import User
from .utils.geocode import get_coords_from_address

class StoreSerializer(serializers.ModelSerializer):
    seller = serializers.SerializerMethodField()

    def get_seller(self, obj):
        user = obj.seller
        return {
            'id': user.id,
            'email': user.email,
            'phone': getattr(user, 'phone', '')
        }
    
    class Meta:
        model = Store
        fields = [
            "id", "seller", "store_name", "opening_time",
            "address", "latitude", "longitude",
            "is_open", "created_at", "updated_at"
        ]
        read_only_fields = ["seller"]


class StoreStep1Serializer(serializers.ModelSerializer):
    store_name = serializers.CharField(max_length=100)
    opening_time = serializers.CharField(max_length=50)
    address_search = serializers.CharField(max_length=200)
    address_detail = serializers.CharField(max_length=200, allow_blank=True, required=False)

    class Meta:
        model = Store
        fields = ["store_name", "opening_time", "address_search", "address_detail"]

    def create(self, validated_data):
        request = self.context["request"]
        user: User = request.user
        if getattr(user, "role", None) != "seller":
            raise serializers.ValidationError({"detail": "판매자만 매장이 가능합니다."})

        # 주소 합치기
        base_addr = validated_data.pop("address_search")
        detail = validated_data.pop("address_detail", "")
        full_address = f"{base_addr} {detail}".strip()

        # 구글 API로 위경도 변환
        lat, lng = get_coords_from_address(full_address)
        if not lat or not lng:
            raise serializers.ValidationError({"address": "주소를 좌표로 변환할 수 없습니다."})

        store = Store.objects.create(
            seller=user,
            store_name=validated_data["store_name"],
            opening_time=validated_data["opening_time"],
            address=full_address,
            latitude=Decimal(str(lat)),
            longitude=Decimal(str(lng)),
        )
        return store

class StoreStep2Serializer(serializers.ModelSerializer):
    store_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Store
        fields = ['store_id', 'business_license', 'permit_doc', 'bank_copy']

    def validate_store_id(self, value):
        request = self.context.get('request')
        store = Store.objects.filter(id=value, seller=request.user).first()
        if not store:
            raise serializers.ValidationError("해당 매장이 존재하지 않거나 권한이 없습니다.")
        return value

    def create(self, validated_data):
        store_id = validated_data.pop('store_id')
        store = Store.objects.get(id=store_id)
        for field, value in validated_data.items():
            setattr(store, field, value)
        store.save()
        return store


