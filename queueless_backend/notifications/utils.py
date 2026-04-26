import json
import logging

from django.conf import settings
from pywebpush import WebPushException, webpush

logger = logging.getLogger(__name__)


def send_web_push(subscription, message_body):
    """
    Send a web push notification to a specific subscription.
    """
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_ADMIN_EMAIL:
        logger.warning("VAPID settings not configured. Skipping Web Push.")
        return None

    registration_info = {
        "endpoint": subscription.endpoint,
        "keys": {
            "p256dh": subscription.p256dh,
            "auth": subscription.auth,
        },
    }

    try:
        response = webpush(
            subscription_info=registration_info,
            data=json.dumps(message_body),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={
                "sub": f"mailto:{settings.VAPID_ADMIN_EMAIL}",
            },
        )
        return response
    except WebPushException as ex:
        logger.error(f"Web Push failed: {ex}")
        if ex.response is not None and ex.response.status_code in [404, 410]:
            # Subscription has expired or is no longer valid
            subscription.delete()
        return None
    except Exception as ex:
        logger.error(f"Unexpected error in Web Push: {ex}")
        return None
