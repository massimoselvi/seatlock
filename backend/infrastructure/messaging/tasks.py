from celery import shared_task
from django.core.mail import send_mail

# A transient broker, database or mail error is retried with growing delays.
RETRY = {
    "autoretry_for": (Exception,),
    "retry_backoff": True,
    "retry_backoff_max": 300,
    "max_retries": 5,
    # Acknowledge after the task ends, so a worker that dies mid-task does not lose it.
    "acks_late": True,
}


# The explicit name keeps messages already in the queue valid across the move.
@shared_task(name="workshops.tasks.promote_waitlist", **RETRY)
def promote_waitlist(workshop_id: int) -> int:
    from infrastructure import container  # imported late: the container imports the queue

    return container.promote_waitlist().execute(workshop_id=workshop_id)


@shared_task(name="workshops.tasks.send_promotion_email", **RETRY)
def send_promotion_email(to: str, workshop_title: str) -> None:
    """One task per person, so a failed email is retried alone and never repeats a promotion."""
    send_mail(
        subject=f"You're in: {workshop_title}",
        message=f"A seat opened up and your spot is confirmed for {workshop_title}.",
        from_email=None,
        recipient_list=[to],
    )


@shared_task(name="workshops.tasks.sweep_waitlists")
def sweep_waitlists() -> int:
    """Runs on a schedule (CELERY_BEAT_SCHEDULE). No retry: the next run is the retry."""
    from infrastructure import container

    return container.sweep_waitlists().execute()
