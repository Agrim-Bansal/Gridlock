from datetime import datetime, timezone


class ModelState:
    def __init__(self) -> None:
        self.status: str = "idle"
        self.last_trained_at: str | None = None

    def set_training(self) -> None:
        self.status = "training"

    def set_ready(self) -> None:
        self.status = "ready"
        self.last_trained_at = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

    def set_idle(self) -> None:
        self.status = "idle"
        self.last_trained_at = None


model_state = ModelState()
