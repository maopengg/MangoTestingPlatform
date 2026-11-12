import base64
import hashlib
import json
from datetime import timedelta

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.utils import timezone

from src.apps.perf.exceptions import (
    PERF_NODE_FAILED,
    PerfError,
)
from src.apps.perf.models import PerfRun, PerfRunNode, PerfRunSecretEnvelope


class PerfSecretService:
    ALGORITHM = "fernet-sha256-v1"

    @staticmethod
    def _cipher():
        digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))

    @classmethod
    def seal(cls, run: PerfRun, values: dict):
        if not values:
            return None
        payload = json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return PerfRunSecretEnvelope.objects.create(
            run=run, cipher_text=cls._cipher().encrypt(payload),
            key_reference=hashlib.sha256(settings.SECRET_KEY.encode()).hexdigest()[:16],
            algorithm=cls.ALGORITHM,
            expires_at=(run.schedule_at or timezone.now()) + timedelta(seconds=run.duration_seconds + 3600),
        )

    @classmethod
    def extend_for_dispatch(cls, run: PerfRun, schedule_at):
        run.secret_envelopes.update(
            expires_at=schedule_at + timedelta(seconds=run.duration_seconds + 3600)
        )

    @classmethod
    def reveal_for_node(cls, node: PerfRunNode):
        envelope = node.run.secret_envelopes.filter(expires_at__gt=timezone.now()).order_by("-create_time").first()
        if not envelope:
            return {}
        try:
            values = json.loads(cls._cipher().decrypt(bytes(envelope.cipher_text)).decode("utf-8"))
        except (InvalidToken, ValueError, json.JSONDecodeError) as error:
            raise PerfError(PERF_NODE_FAILED) from error
        if envelope.consumed_at is None:
            envelope.consumed_at = timezone.now()
            envelope.save(update_fields=["consumed_at"])
        return values
