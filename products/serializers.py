from rest_framework import serializers
from django.utils import timezone
from .models import Product
from stores.models import Store

class ProductReadSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    store = serializers.SerializerMethodField()

    def get_store(self, obj):                 
        store = obj.store
        return {
            "id": store.id,
            "name": getattr(store, "store_name", ""),
            "lat": getattr(store, "latitude", None),
            "lng": getattr(store, "longitude", None),
        }

    class Meta:
        model = Product
        fields = [
            "id", "store", "store_name",
            "category", "category_name",
            "image", "name", "description",
            "price", "discount_price", "discount_rate",
            "stock", "expiration_date", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "store", "is_active", "created_at", "updated_at"]

class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "category",
            "image",
            "name",
            "description",
            "price",
            "discount_price",
            "stock",
            "expiration_date",
            "is_active",
        ]
        extra_kwargs = { # 필수 아님
            "description": {"required": False, "allow_null": True, "allow_blank": True}
        }

    def validate(self, attrs):
        price = attrs.get("price")
        discount_price = attrs.get("discount_price")
        stock = attrs.get("stock")
        expiration_date = attrs.get("expiration_date")

        if price is not None and price <= 0:
            raise serializers.ValidationError({"price": "원 가격은 0보다 커야 함."})

        # 생성/수정 분기
        if self.instance is None:
            # Create
            if stock is None or stock < 1:
                raise serializers.ValidationError({"stock": "신규 등록 시 수량은 1 이상이어야 합니다."})
        else:
            # Update
            if stock is not None and stock < 0:
                raise serializers.ValidationError({"stock": "수량은 0 이상이어야 합니다."})

        if discount_price is not None:
            if discount_price <= 0:
                raise serializers.ValidationError({"discount_price": "최종 판매 가격은 0보다 커야 함."})
            if price is not None and discount_price > price:
                raise serializers.ValidationError({"discount_price": "최종 판매 가격은 원 가격보다 클 수 없음."})

        if expiration_date is not None and expiration_date <= timezone.now():
            raise serializers.ValidationError({"expiration_date": "유통기한은 현재 시각 이후여야 함."})

        return attrs
    
    #할인율 계산
    def _calc_discount_rate(self, price, discount_price):
        if price and discount_price:
            return round((price - discount_price) / price * 100)
        return None

    #판매자 id 가져오기
    def _get_sellers_store(self, user):
        try:
            return Store.objects.get(seller=user)  # 1:1 
        except Store.DoesNotExist:
            raise serializers.ValidationError({
                "store": "현재 로그인한 판매자 계정으로 등록된 매장이 없습니다. 매장 가입을 먼저 완료하세요."
            })

    #POST
    def create(self, validated_data):
        request = self.context["request"]
        store = self._get_sellers_store(request.user)
        validated_data["store"] = store
        
        validated_data["discount_rate"] = self._calc_discount_rate(
        validated_data.get("price"),
        validated_data.get("discount_price")
        )
        return super().create(validated_data)

    #PATCH
    def update(self, instance, validated_data):
        validated_data.pop("store", None)
        
        # price나 discount_price가 변경되었으면 할인율 재계산
        price = validated_data.get("price", instance.price)
        discount_price = validated_data.get("discount_price", instance.discount_price)
        validated_data["discount_rate"] = self._calc_discount_rate(price, discount_price)
        
        return super().update(instance, validated_data)
