from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from apps.common.responses import success_response, error_response
from apps.common.permissions import IsPatient
from .services import RegisterUserService, AuthService
from .serializers import (
    RegisterPatientSerializer,
    LoginSerializer,
    UserSerializer,
    TokenSerializer,
)


@extend_schema(tags=['Auth'], summary='Register a new patient account')
class RegisterPatientView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterPatientSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = RegisterUserService.register_patient(
                username=serializer.validated_data['username'],
                email=serializer.validated_data.get('email', ''),
                password=serializer.validated_data['password'],
                phone_number=serializer.validated_data.get('phone_number', ''),
            )
        except ValueError as e:
            return error_response(errors={'detail': str(e)}, status_code=400)

        tokens = AuthService.get_tokens_for_user(user)
        return success_response(
            data={**TokenSerializer(tokens).data, 'user': UserSerializer(user).data},
            message='Patient registered successfully.',
            status_code=201,
        )


@extend_schema(tags=['Auth'], summary='Login with username and password')
class LoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = AuthService.authenticate(
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password'],
            )
        except ValueError as e:
            return error_response(errors={'detail': str(e)}, status_code=401)

        tokens = AuthService.get_tokens_for_user(user)
        return success_response(
            data={**TokenSerializer(tokens).data, 'user': UserSerializer(user).data},
            message='Login successful.',
        )


@extend_schema(tags=['Auth'], summary='Get current user profile')
class MeView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request):
        serializer = UserSerializer(request.user)
        return success_response(data=serializer.data)
