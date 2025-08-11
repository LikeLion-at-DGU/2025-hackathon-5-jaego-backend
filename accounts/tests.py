from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

class ConsumerAuthTests(APITestCase):
    def setUp(self):
        self.signup_url = reverse('consumer-signup')  # /accounts/consumer/signup
        self.login_url = reverse('consumer-login')    # /accounts/consumer/login
        self.me_url = reverse('consumer-me')          # /accounts/consumer/me
        self.token_refresh_url = reverse('token_refresh')  # /accounts/token/refresh/
        self.logout_url = reverse('logout')           # /accounts/logout

        self.user_data = {
            "email": "testconsumer@example.com",
            "password": "strongpassword123",
            "name": "테스트소비자",
            "phone": "01012345678"
        }

    def test_consumer_signup_login_me_flow(self):
        # 회원가입
        response = self.client.post(self.signup_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        # 로그인
        login_data = {
            "email": self.user_data['email'],
            "password": self.user_data['password']
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access_token = response.data.get('access')
        refresh_token = response.data.get('refresh')
        self.assertIsNotNone(access_token)
        self.assertIsNotNone(refresh_token)

        # 내 정보 조회 (인증 필요)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user_data['email'])
        self.assertEqual(response.data['name'], self.user_data['name'])

        # 토큰 리프레시
        response = self.client.post(self.token_refresh_url, {"refresh": refresh_token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        new_access_token = response.data['access']

        # 로그아웃 (refresh token 무효화)
        response = self.client.post(self.logout_url, {"refreshToken": refresh_token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # 로그아웃 후 리프레시 토큰으로 재발급 시도 (실패 예상)
        response = self.client.post(self.token_refresh_url, {"refresh": refresh_token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
