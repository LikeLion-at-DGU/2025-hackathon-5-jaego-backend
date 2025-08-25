from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


# (1) 소비자
class ConsumerSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'password2', 'name', 'phone')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "비밀번호가 일치하지 않습니다."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data['name'],
            phone=validated_data['phone'],
            role='consumer'
        )
        return user

class ConsumerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'name', 'phone', 'created_at')
        read_only_fields = ('id', 'email', 'created_at')


# (2) 판매자
class SellerSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'password2', 'name', 'phone')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "비밀번호가 일치하지 않습니다."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data['name'],
            phone=validated_data['phone'],
            role='seller'
        )
        return user

class SellerSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.store_name", read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'email', 'store_name', 'name', 'phone', 'created_at')
        read_only_fields = ('id', 'email', 'created_at', 'store_name')
        


