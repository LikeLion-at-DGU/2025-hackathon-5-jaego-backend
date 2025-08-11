from rest_framework import serializers
from decimal import Decimal, InvalidOperation
from .models import Store
from accounts.models import User

class StoreStep1Serializer(serializers.ModelSerializer):
    store_name = serializers.CharField(max_length=100)
    opening_time = serializers.CharField(max_length=50)
    address_search = serializers.CharField(max_length=200)
    address_detail = serializers.CharField(max_length=200, allow_blank=True, required=False)
    latitude = serializers.CharField() 
    longitude = serializers.CharField()

    class Meta:
        model = Store
        fields = [
            "store_name",
            "opening_time",
            "address_search",
            "address_detail",
            "latitude",
            "longitude",
        ]

    def validate(self, attrs):
        # 위도 경도 검증(숫자/범위)
        try:
            lat = Decimal(str(attrs.get("latitude")))
            lng = Decimal(str(attrs.get("longitude")))
        except (InvalidOperation, TypeError, ValueError):
            raise serializers.ValidationError({"latitude": "유효한 숫자여야 합니다.", "longitude": "유효한 숫자여야 합니다."})

        if not (-90 <= float(lat) <= 90):
            raise serializers.ValidationError({"latitude": "위도는 -90 ~ 90 사이여야 합니다."})
        if not (-180 <= float(lng) <= 180):
            raise serializers.ValidationError({"longitude": "경도는 -180 ~ 180 사이여야 합니다."})

        attrs["latitude"] = lat
        attrs["longitude"] = lng
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        user: User = request.user
        if getattr(user, "role", None) != "seller":
            raise serializers.ValidationError({"detail": "판매자만 매장을 등록할 수 있습니다."})

        # 주소 합치기
        base_addr = validated_data.pop("address_search")
        detail = validated_data.pop("address_detail", "")
        address = f"{base_addr} {detail}".strip()

        store = Store.objects.create(
            seller=user,
            store_name=validated_data["store_name"],
            opening_time=validated_data["opening_time"],
            address=address,
            latitude=validated_data["latitude"],
            longitude=validated_data["longitude"],
            # 기본값: is_open=False, category=None, description=""
        )
        return store


class StoreReadSerializer(serializers.ModelSerializer):
    seller_id = serializers.IntegerField(source="seller.id", read_only=True)

    class Meta:
        model = Store
        fields = [
            "id", "seller_id", "store_name", "opening_time",
            "address", "latitude", "longitude",
            "is_open", "created_at", "updated_at"
        ]
        read_only_fields = ["seller"]

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
