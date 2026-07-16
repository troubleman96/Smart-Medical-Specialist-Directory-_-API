import random
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from .models import PhoneOTP

User = get_user_model()


def _normalize_phone(phone_number):
    from apps.notifications.services import SmsService
    try:
        return SmsService.normalize_phone(phone_number)
    except ValueError:
        raise ValueError('Enter a valid Tanzania phone number (e.g. 0712345678).')


def _derive_username(phone_number):
    return phone_number.lstrip('+')


class RegisterUserService:
    @staticmethod
    def register_patient(phone_number, password, full_name='', username='', email=''):
        normalized_phone = _normalize_phone(phone_number)
        if User.objects.filter(phone_number=normalized_phone).exists():
            raise ValueError('An account with this phone number already exists.')

        username = username or _derive_username(normalized_phone)
        if User.objects.filter(username=username).exists():
            raise ValueError('Username already exists.')
        if email and User.objects.filter(email=email).exists():
            raise ValueError('Email already exists.')

        user = User.objects.create(
            username=username,
            full_name=full_name,
            email=email,
            password=make_password(password),
            role=User.Role.PATIENT,
            phone_number=normalized_phone,
        )
        return user

    @staticmethod
    def register_hospital_admin(phone_number, password, hospital, username='', email=''):
        normalized_phone = _normalize_phone(phone_number)
        if User.objects.filter(phone_number=normalized_phone).exists():
            raise ValueError('An account with this phone number already exists.')

        username = username or _derive_username(normalized_phone)
        if User.objects.filter(username=username).exists():
            raise ValueError('Username already exists.')
        if email and User.objects.filter(email=email).exists():
            raise ValueError('Email already exists.')

        user = User.objects.create(
            username=username,
            email=email,
            password=make_password(password),
            role=User.Role.HOSPITAL_ADMIN,
            hospital=hospital,
            phone_number=normalized_phone,
        )
        return user

    @staticmethod
    def register_super_admin(phone_number, password, username='', email=''):
        normalized_phone = _normalize_phone(phone_number)
        if User.objects.filter(phone_number=normalized_phone).exists():
            raise ValueError('An account with this phone number already exists.')

        username = username or _derive_username(normalized_phone)
        if User.objects.filter(username=username).exists():
            raise ValueError('Username already exists.')
        if email and User.objects.filter(email=email).exists():
            raise ValueError('Email already exists.')

        user = User.objects.create(
            username=username,
            email=email,
            password=make_password(password),
            role=User.Role.SUPER_ADMIN,
            phone_number=normalized_phone,
        )
        return user


class AuthService:
    @staticmethod
    def get_tokens_for_user(user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        if user.hospital_id:
            refresh['hospital_id'] = user.hospital_id
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    @staticmethod
    def authenticate(phone_number, password):
        try:
            normalized_phone = _normalize_phone(phone_number)
            user = User.objects.get(phone_number=normalized_phone)
        except (ValueError, User.DoesNotExist):
            raise ValueError('Invalid credentials.')

        if not user.check_password(password):
            raise ValueError('Invalid credentials.')

        return user


class OtpService:
    TTL_MINUTES = 10

    @staticmethod
    def generate_and_send(user):
        code = f'{random.randint(0, 999999):06d}'
        expires_at = timezone.now() + timedelta(minutes=OtpService.TTL_MINUTES)
        PhoneOTP.objects.create(user=user, code=code, expires_at=expires_at)

        from apps.notifications.services import NotificationDispatcher
        NotificationDispatcher.otp_verification(user, code)
        return code

    @staticmethod
    def verify(user, code):
        otp = PhoneOTP.objects.filter(
            user=user, code=code, consumed_at__isnull=True,
        ).order_by('-created_at').first()

        if not otp:
            raise ValueError('Invalid verification code.')
        if otp.expires_at < timezone.now():
            raise ValueError('Verification code has expired. Request a new one.')

        otp.consumed_at = timezone.now()
        otp.save(update_fields=['consumed_at'])

        user.phone_verified = True
        user.save(update_fields=['phone_verified'])
        return user
