import requests
import re
from django.conf import settings
from django.utils import timezone
from apps.notifications.models import NotificationLog
from apps.common.enums import NotificationChannel, NotificationStatus


class SmsDeliveryError(Exception):
    pass


class SmsService:
    # Tanzania mobile numbers: 9 digits after the +255 country code, starting
    # with 6 or 7 (covers all current carriers/prefixes, not just a fixed list).
    LOCAL_NUMBER_RE = re.compile(r'[67]\d{8}')

    @staticmethod
    def normalize_phone(phone_number):
        cleaned = re.sub(r'[\s\-\(\)]', '', phone_number)
        if cleaned.startswith('+255'):
            digits = cleaned[4:]
        elif cleaned.startswith('255'):
            digits = cleaned[3:]
        elif cleaned.startswith('0'):
            digits = cleaned[1:]
        else:
            digits = cleaned

        if not SmsService.LOCAL_NUMBER_RE.fullmatch(digits):
            raise ValueError(f'Invalid Tanzania phone number: {phone_number}')

        return f'+255{digits}'

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
    def appointment_requested(appointment):
        message = (
            f"Your appointment request {appointment.reference_number} has been received.\n"
            f"Specialist: Dr. {appointment.specialist.full_name}\n"
            f"Hospital: {appointment.hospital.name}\n"
            f"Date: {appointment.scheduled_at.strftime('%d %B %Y at %H:%M')}\n"
            f"We'll SMS you once the hospital confirms."
        )
        return NotificationDispatcher._send(
            phone_number=appointment.patient.phone_number,
            message=message,
            appointment=appointment,
        )

    @staticmethod
    def new_booking_for_hospital(appointment):
        hospital = appointment.hospital
        phone = hospital.phone
        if not phone:
            return None

        message = (
            f"New booking!\n"
            f"Patient: {appointment.patient.full_name or appointment.patient.username}\n"
            f"Specialist: Dr. {appointment.specialist.full_name} ({appointment.specialist.specialization})\n"
            f"Reference: {appointment.reference_number}\n"
            f"Date: {appointment.scheduled_at.strftime('%d %B %Y at %H:%M')}\n"
            f"Please confirm or cancel this appointment."
        )
        return NotificationDispatcher._send(
            phone_number=phone,
            message=message,
            appointment=appointment,
        )

    @staticmethod
    def otp_verification(user, code):
        message = (
            f"Your Kindamba verification code is {code}. "
            f"It expires in 10 minutes. Do not share this code with anyone."
        )
        return NotificationDispatcher._send(phone_number=user.phone_number, message=message)

    @staticmethod
    def hospital_registration_received(hospital, admin_phone):
        message = (
            f"Kindamba: Registration received for '{hospital.name}'.\n"
            f"Your application is pending verification. We'll SMS you once it's reviewed."
        )
        return NotificationDispatcher._send(phone_number=admin_phone, message=message)

    @staticmethod
    def hospital_verified(hospital, admin_phone):
        message = (
            f"Kindamba: Congratulations! '{hospital.name}' has been verified and is now live.\n"
            f"Patients can now find and book your specialists."
        )
        return NotificationDispatcher._send(phone_number=admin_phone, message=message)

    @staticmethod
    def hospital_suspended(hospital, admin_phone):
        message = (
            f"Kindamba: '{hospital.name}' has been suspended on Kindamba.\n"
            f"Contact support for details."
        )
        return NotificationDispatcher._send(phone_number=admin_phone, message=message)

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
