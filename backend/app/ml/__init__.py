from app.ml.predictor import Predictor
from app.ml.spectral_ridge import SpectralRidgePredictor
from app.ml.stub import StubPredictor

_REGISTRY: dict[str, type] = {
    "stub": StubPredictor,
    "spectral": SpectralRidgePredictor,
}

_instance: Predictor | None = None


def get_predictor() -> Predictor:
    global _instance
    if _instance is None:
        from app.config import settings

        cls = _REGISTRY[settings.predictor]
        _instance = cls()
    return _instance


def reset_predictor() -> None:
    global _instance
    _instance = None
