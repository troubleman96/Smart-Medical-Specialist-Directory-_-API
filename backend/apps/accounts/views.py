from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema
from apps.common.responses import success_response, error_response
from .services import RegisterUserService, AuthService, OtpService
from .serializers import (
    RegisterPatientSerializer,
    LoginSerializer,
    UserSerializer,
    TokenSerializer,
    VerifyOtpSerializer,
)


def _send_otp(user):
    try:
        OtpService.generate_and_send(user)
    except Exception:
        pass


@extend_schema(tags=['Auth'], summary='Register a new patient account')
class RegisterPatientView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterPatientSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = RegisterUserService.register_patient(
                phone_number=serializer.validated_data['phone_number'],
                password=serializer.validated_data['password'],
                username=serializer.validated_data.get('username', ''),
                email=serializer.validated_data.get('email', ''),
            )
        except ValueError as e:
            return error_response(errors={'detail': str(e)}, status_code=400)

        _send_otp(user)

        tokens = AuthService.get_tokens_for_user(user)
        return success_response(
            data={**TokenSerializer(tokens).data, 'user': UserSerializer(user).data},
            message='Patient registered successfully. A verification code has been sent by SMS.',
            status_code=201,
        )


@extend_schema(tags=['Auth'], summary='Login with phone number and password')
class LoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = AuthService.authenticate(
                phone_number=serializer.validated_data['phone_number'],
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


@extend_schema(tags=['Auth'], summary='Verify phone number with the SMS OTP code')
class VerifyOtpView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VerifyOtpSerializer

    def post(self, request):
        if request.user.phone_verified:
            return success_response(data=UserSerializer(request.user).data, message='Phone already verified.')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = OtpService.verify(request.user, serializer.validated_data['code'])
        except ValueError as e:
            return error_response(errors={'detail': str(e)}, status_code=400)

        return success_response(data=UserSerializer(user).data, message='Phone number verified.')


@extend_schema(tags=['Auth'], summary='Resend the SMS OTP verification code')
class ResendOtpView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.phone_verified:
            return success_response(message='Phone already verified.')

        _send_otp(request.user)
        return success_response(message='Verification code sent.')
