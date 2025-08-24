from rest_framework.permissions import BasePermission

# 판매자 권한
class IsSeller(BasePermission):
    message = "판매자만 접근할 수 있습니다."

    def has_permission(self, request, view):
        return bool(
            request.user 
            and request.user.is_authenticated 
            and getattr(request.user, "role", None) == "seller"
        )

# 소비자 권한
class IsConsumer(BasePermission):
    message = "소비자만 접근할 수 있습니다."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "consumer"
        )