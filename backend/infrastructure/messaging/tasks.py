from celery import shared_task


# The explicit name keeps messages already in the queue valid across the move.
@shared_task(name="workshops.tasks.promote_waitlist")
def promote_waitlist(workshop_id: int) -> int:
    from infrastructure import container  # imported late: the container imports the queue

    return container.promote_waitlist().execute(workshop_id=workshop_id)
