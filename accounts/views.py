from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model

from .serializers import *

User = get_user_model()

class ConsumerViewSet(viewsets.GenericViewSet):
    serializer_class = ConsumerSerializer
    queryset = User.objects.filter(role='consumer')

    def get_permissions(self):
        if self.action in ['signup', 'login']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['post'])
    def signup(self, request):
        serializer = ConsumerSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "user": ConsumerSerializer(user).data,
            "auth": {
                "tokenType": "Bearer",
                "accessToken": str(refresh.access_token),
                "refreshToken": str(refresh),
            }
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def login(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(request, email=email, password=password)

        if user is not None and user.role == 'consumer':
            refresh = RefreshToken.for_user(user)
            return Response({
                "user": ConsumerSerializer(user).data,
                "auth": {
                    "tokenType": "Bearer",
                    "accessToken": str(refresh.access_token),
                    "refreshToken": str(refresh),
                }
            })
        return Response({"detail": "이메일 또는 비밀번호가 올바르지 않습니다."},
                        status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['get'])
    def me(self, request):
        user = request.user
        if user.role != 'consumer':
            return Response({"detail": "소비자만 접근 가능합니다."}, status=status.HTTP_403_FORBIDDEN)
        serializer = ConsumerSerializer(user)
        return Response(serializer.data)

########################################################
# (2) Seller
class SellerViewSet(viewsets.GenericViewSet):
    serializer_class = SellerSerializer
    queryset = User.objects.filter(role='seller')

    def get_permissions(self):
        if self.action in ['signup', 'login']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['post'])
    def signup(self, request):
        serializer = SellerSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "user": SellerSerializer(user).data,
            "auth": {
                "tokenType": "Bearer",
                "accessToken": str(refresh.access_token),
                "refreshToken": str(refresh),
            }
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def login(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(request, email=email, password=password)

        if user is not None and user.role == 'seller':
            refresh = RefreshToken.for_user(user)
            return Response({
                "user": SellerSerializer(user).data,
                "auth": {
                    "tokenType": "Bearer",
                    "accessToken": str(refresh.access_token),
                    "refreshToken": str(refresh),
                }
            })
        return Response({"detail": "이메일 또는 비밀번호가 올바르지 않습니다."},
                        status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['get'])
    def me(self, request):
        user = request.user
        if user.role != 'seller':
            return Response({"detail": "판매자만 접근 가능합니다."}, status=status.HTTP_403_FORBIDDEN)
        serializer = SellerSerializer(user)
        return Response(serializer.data)

######################################################################
#(3) 로그아웃 ( seller, consumer 둘 다 사용 가능 )

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if refresh_token is None:
            return Response({"detail": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except (TokenError, InvalidToken) as e:
            return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Logout successful."}, status=status.HTTP_205_RESET_CONTENT)