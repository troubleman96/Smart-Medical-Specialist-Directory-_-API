import requests
import re
from django.conf import settings
from django.utils import timezone
from apps.notifications.models import NotificationLog
from apps.common.enums import NotificationChannel, NotificationStatus


class SmsDeliveryError(Exception):
    pass


class SmsService:
    VALID_TZ_PREFIXES = ['071', '072', '073', '074', '075', '076', '077', '078']

    @staticmethod
    def normalize_phone(phone_number):
        cleaned = re.sub(r'[\s\-\(\)]', '', phone_number)
        if cleaned.startswith('+255'):
            return cleaned
        if cleaned.startswith('255'):
            return f'+{cleaned}'
        if cleaned.startswith('0') and cleaned[:3] in SmsService.VALID_TZ_PREFIXES:
            return f'+255{cleaned[1:]}'
        raise ValueError(f'Invalid Tanzania phone number: {phone_number}')

    @staticmethod
    def send(phone_number, message):
        normalized = SmsService.normalize_phone(phone_number)
        api_key = getattr(settings, 'SENDAFRICA_API_KEY', '')
        base_url = getattr(settings, 'SENDAFRICA_BASE_URL', 'https://api.sendafrica.online')

        if not api_key:
            raise SmsDeliveryError('SENDAFRICA_API_KEY is not configured.')

        try:
            response = requests.post(
                f'{base_url}/v1/sms/',
                headers={
                    'X-API-Key': api_key,
                    'Content-Type': 'application/json',
                },
                json={
                    'to': normalized,
                    'message': message,
                },
                timeout=10,
            )
            data = response.json()

            if not data.get('success'):
                error_code = data.get('error', {}).get('code', 'unknown')
                error_msg = data.get('error', {}).get('message', 'Unknown error')
                raise SmsDeliveryError(f'[{error_code}] {error_msg}')

            return data['data']

        except requests.RequestException as e:
            raise SmsDeliveryError(f'Network error: {str(e)}')


class NotificationDispatcher:
    @staticmethod
    def appointment_confirmed(appointment):
        message = (
            f"Your appointment {appointment.reference_number} has been confirmed.\n"
            f"Specialist: Dr. {appointment.specialist.full_name}\n"
            f"Hospital: {appointment.hospital.name}\n"
            f"Date: {appointment.scheduled_at.strftime('%d %B %Y at %H:%M')}\n"
            f"Please arrive 15 minutes early."
        )
        return NotificationDispatcher._send(
            phone_number=appointment.patient.phone_number,
            message=message,
            appointment=appointment,
        )

    @staticmethod
    def appointment_cancelled(appointment):
        message = (
            f"Your appointment {appointment.reference_number} has been cancelled.\n"
            f"Specialist: Dr. {appointment.specialist.full_name}\n"
            f"Hospital: {appointment.hospital.name}\n"
            f"If you have questions, please contact the hospital directly."
        )
        return NotificationDispatcher._send(
            phone_number=appointment.patient.phone_number,
            message=message,
            appointment=appointment,
        )

    @staticmethod
    def appointment_reminder(appointment):
        message = (
            f"Reminder: You have an appointment tomorrow.\n"
            f"Reference: {appointment.reference_number}\n"
            f"Specialist: Dr. {appointment.specialist.full_name}\n"
            f"Hospital: {appointment.hospital.name}\n"
            f"Date: {appointment.scheduled_at.strftime('%d %B %Y at %H:%M')}"
        )
        return NotificationDispatcher._send(
            phone_number=appointment.patient.phone_number,
            message=message,
            appointment=appointment,
        )

    @staticmethod
    def _send(phone_number, message, appointment=None):
        if not phone_number:
            log = NotificationLog.objects.create(
                recipient='unknown',
                channel=NotificationChannel.SMS,
                message=message,
                status=NotificationStatus.FAILED,
                provider_response={'error': 'No phone number provided'},
                appointment=appointment,
            )
            return log

        log = NotificationLog.objects.create(
            recipient=phone_number,
            channel=NotificationChannel.SMS,
            message=message,
            status=NotificationStatus.PENDING,
            appointment=appointment,
        )

        from apps.notifications.tasks import send_sms_task
        send_sms_task.delay(log.id)

        return log
