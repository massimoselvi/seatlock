from application.workshops.interfaces import WaitlistPromotionQueue

from .tasks import promote_waitlist


class CeleryWaitlistPromotionQueue(WaitlistPromotionQueue):
    def enqueue(self, workshop_id: int) -> None:
        promote_waitlist.delay(workshop_id)
