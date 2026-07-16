from celery import shared_task
from django.utils import timezone
from apps.notifications.models import NotificationLog
from apps.common.enums import NotificationStatus


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_sms_task(self, notification_log_id):
    try:
        log = NotificationLog.objects.get(id=notification_log_id)
    except NotificationLog.DoesNotExist:
        return

    from apps.notifications.services import SmsService, SmsDeliveryError

    try:
        result = SmsService.send(log.recipient, log.message)
        log.status = NotificationStatus.SENT
        log.provider_response = result
        log.sent_at = timezone.now()
        log.save(update_fields=['status', 'provider_response', 'sent_at', 'updated_at'])
    except SmsDeliveryError as exc:
        log.status = NotificationStatus.FAILED
        log.provider_response = {'error': str(exc)}
        log.save(update_fields=['status', 'provider_response', 'updated_at'])

        raise self.retry(exc=exc)
