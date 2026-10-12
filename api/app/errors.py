"""Errors the API turns into a status code and a message a person can read."""

from __future__ import annotations

from datetime import datetime


class ApiError(Exception):
    status = 400
    code = "bad_request"

    def __init__(self, message: str, **detail: object) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class NotFound(ApiError):
    status = 404
    code = "not_found"


class SpeechRejected(ApiError):
    status = 422
    code = "speech_detected"

    def __init__(self, probability: float, threshold: float) -> None:
        super().__init__(
            f"This clip sounds like mostly speech ({probability:.0%} of it), so it was not posted. "
            "Sonic Postcards only keeps ambient sound, to protect the people around you. "
            "Try again when nobody is talking close to the microphone.",
            speech_probability=probability,
            threshold=threshold,
        )


class RateLimited(ApiError):
    status = 429
    code = "rate_limited"

    def __init__(self, limit: int, resets_at: datetime | None) -> None:
        super().__init__(
            f"You have sent {limit} postcards in the last 24 hours, which is the limit. Come back a little later.",
            limit=limit,
            resets_at=resets_at.isoformat() if resets_at else None,
        )
        self.resets_at = resets_at


class BadClip(ApiError):
    status = 400

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class TooLarge(ApiError):
    status = 413
    code = "too_large"


class Unauthorized(ApiError):
    status = 401
    code = "unauthorized"


class AdminDisabled(ApiError):
    status = 503
    code = "admin_disabled"
