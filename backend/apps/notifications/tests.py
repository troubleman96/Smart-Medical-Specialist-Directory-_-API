import pytest
from unittest.mock import patch, MagicMock
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.hospitals.models import Hospital
from apps.specialists.models import Specialist
from apps.appointments.models import Appointment
from apps.appointments.services import AppointmentService
from apps.notifications.models import NotificationLog
from apps.notifications.services import SmsService, SmsDeliveryError, NotificationDispatcher
from apps.common.enums import HospitalStatus, AppointmentStatus, NotificationStatus

User = get_user_model()


@pytest.fixture
def notification_setup():
    hospital = Hospital.objects.create(
        name='Test Hospital',
        registration_no='REG-001',
        latitude=-6.7924,
        longitude=39.2083,
        address='123 Test Street',
        phone='+255712345678',
        email='hospital@test.com',
        status=HospitalStatus.VERIFIED,
    )
    admin = User.objects.create_user(
        username='hospitaladmin',
        email='admin@hospital.com',
        password='securepass123',
        role='HOSPITAL_ADMIN',
        hospital=hospital,
    )
    patient = User.objects.create_user(
        username='patient1',
        email='patient@test.com',
        password='securepass123',
        role='PATIENT',
        phone_number='+255712345678',
    )
    specialist = Specialist.objects.create(
        hospital=hospital,
        full_name='Dr. Amina Juma',
        specialization='Cardiology',
        license_no='TLC-001',
        created_by=admin,
    )
    appointment = AppointmentService.create(
        patient=patient,
        specialist_id=specialist.id,
        hospital_id=hospital.id,
        scheduled_at=timezone.now() + timedelta(days=1),
    )
    return hospital, admin, patient, specialist, appointment


@pytest.mark.django_db
class TestSmsServiceNormalize:
    def test_normalize_local_format(self):
        assert SmsService.normalize_phone('0712345678') == '+255712345678'

    def test_normalize_international_with_plus(self):
        assert SmsService.normalize_phone('+255712345678') == '+255712345678'

    def test_normalize_international_without_plus(self):
        assert SmsService.normalize_phone('255712345678') == '+255712345678'

    def test_normalize_with_dashes(self):
        assert SmsService.normalize_phone('071-234-5678') == '+255712345678'

    def test_normalize_with_spaces(self):
        assert SmsService.normalize_phone('071 234 5678') == '+255712345678'

    def test_normalize_invalid_number(self):
        with pytest.raises(ValueError, match='Invalid Tanzania phone'):
            SmsService.normalize_phone('+254712345678')


@pytest.mark.django_db
class TestSmsServiceSend:
    @patch('apps.notifications.services.requests.post')
    def test_send_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            'success': True,
            'data': {'message_id': 'test-123', 'status': 'sent'},
        }
        mock_post.return_value = mock_resp

        result = SmsService.send('+255712345678', 'Test message')
        assert result['message_id'] == 'test-123'
        mock_post.assert_called_once()

    @patch('apps.notifications.services.requests.post')
    def test_send_failure(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            'success': False,
            'error': {'code': 'invalid_phone', 'message': 'Invalid phone'},
        }
        mock_post.return_value = mock_resp

        with pytest.raises(SmsDeliveryError):
            SmsService.send('+255712345678', 'Test message')


@pytest.mark.django_db
class TestNotificationDispatcher:
    def test_appointment_confirmed_creates_log(self, notification_setup):
        _, _, _, _, appointment = notification_setup
        appointment.status = AppointmentStatus.CONFIRMED
        appointment.save()

        log = NotificationDispatcher.appointment_confirmed(appointment)
        assert log.status == NotificationStatus.PENDING
        assert log.recipient == '+255712345678'
        assert appointment.reference_number in log.message

    def test_appointment_cancelled_creates_log(self, notification_setup):
        _, _, _, _, appointment = notification_setup
        log = NotificationDispatcher.appointment_cancelled(appointment)
        assert log.status == NotificationStatus.PENDING
        assert 'cancelled' in log.message.lower()

    def test_no_phone_number_logs_failure(self, notification_setup):
        _, _, patient, _, appointment = notification_setup
        patient.phone_number = ''
        patient.save()
        log = NotificationDispatcher._send('', 'Test', appointment)
        assert log.status == NotificationStatus.FAILED

    def test_appointment_requested_creates_log(self, notification_setup):
        _, _, _, _, appointment = notification_setup
        log = NotificationDispatcher.appointment_requested(appointment)
        assert log.status == NotificationStatus.PENDING
        assert log.recipient == '+255712345678'
        assert appointment.reference_number in log.message
        assert 'received' in log.message.lower()

    def test_otp_verification_creates_log(self, notification_setup):
        _, _, patient, _, _ = notification_setup
        log = NotificationDispatcher.otp_verification(patient, '123456')
        assert log.status == NotificationStatus.PENDING
        assert log.recipient == '+255712345678'
        assert '123456' in log.message

    def test_hospital_registration_received_creates_log(self, notification_setup):
        hospital, _, _, _, _ = notification_setup
        log = NotificationDispatcher.hospital_registration_received(hospital, '+255754111222')
        assert log.status == NotificationStatus.PENDING
        assert log.recipient == '+255754111222'
        assert hospital.name in log.message
        assert 'pending' in log.message.lower()

    def test_hospital_verified_creates_log(self, notification_setup):
        hospital, _, _, _, _ = notification_setup
        log = NotificationDispatcher.hospital_verified(hospital, '+255754111222')
        assert log.status == NotificationStatus.PENDING
        assert hospital.name in log.message
        assert 'verified' in log.message.lower()

    def test_hospital_suspended_creates_log(self, notification_setup):
        hospital, _, _, _, _ = notification_setup
        log = NotificationDispatcher.hospital_suspended(hospital, '+255754111222')
        assert log.status == NotificationStatus.PENDING
        assert hospital.name in log.message
        assert 'suspended' in log.message.lower()
