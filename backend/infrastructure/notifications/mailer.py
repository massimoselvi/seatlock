from django.core.mail import send_mail

from application.workshops.interfaces import PromotionNotifier
from domain.workshops.entities import Registration, Workshop


class EmailPromotionNotifier(PromotionNotifier):
    def notify(self, registration: Registration, workshop: Workshop) -> None:
        if not registration.user_email:
            return
        send_mail(
            subject=f"You're in: {workshop.title}",
            message=f"A seat opened up and your spot is confirmed for {workshop.title}.",
            from_email=None,
            recipient_list=[registration.user_email],
        )
