from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class RegisterUserService:
    @staticmethod
    def register_patient(username, email, password, phone_number=''):
        if User.objects.filter(username=username).exists():
            raise ValueError('Username already exists.')
        if email and User.objects.filter(email=email).exists():
            raise ValueError('Email already exists.')

        user = User.objects.create(
            username=username,
            email=email,
            password=make_password(password),
            role=User.Role.PATIENT,
            phone_number=phone_number,
        )
        return user

    @staticmethod
    def register_hospital_admin(username, email, password, hospital, phone_number=''):
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
            phone_number=phone_number,
        )
        return user

    @staticmethod
    def register_super_admin(username, email, password):
        if User.objects.filter(username=username).exists():
            raise ValueError('Username already exists.')
        if email and User.objects.filter(email=email).exists():
            raise ValueError('Email already exists.')

        user = User.objects.create(
            username=username,
            email=email,
            password=make_password(password),
            role=User.Role.SUPER_ADMIN,
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
    def authenticate(username, password):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise ValueError('Invalid credentials.')

        if not user.check_password(password):
            raise ValueError('Invalid credentials.')

        return user
