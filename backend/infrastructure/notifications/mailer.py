from application.workshops.interfaces import PromotionNotifier
from domain.workshops.entities import Registration, Workshop
from infrastructure.messaging.tasks import send_promotion_email


class EmailPromotionNotifier(PromotionNotifier):
    """Hands the email to Celery, which retries it. Sending inline would lose it on any error."""

    def notify(self, registration: Registration, workshop: Workshop) -> None:
        if not registration.user_email:
            return
        send_promotion_email.delay(registration.user_email, workshop.title)
