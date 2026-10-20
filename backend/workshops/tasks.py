from celery import shared_task
from django.core.mail import send_mail

from .models import Workshop
from .services import promote_waitlisted


@shared_task
def promote_waitlist(workshop_id: int) -> int:
    promoted = promote_waitlisted(workshop_id=workshop_id)
    workshop = Workshop.objects.get(pk=workshop_id)
    for registration in promoted:
        if registration.user.email:
            send_mail(
                subject=f"You're in: {workshop.title}",
                message=f"A seat opened up and your spot is confirmed for {workshop.title}.",
                from_email=None,
                recipient_list=[registration.user.email],
            )
    return len(promoted)
