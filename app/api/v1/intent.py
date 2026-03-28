"""Endpoint de clasificación de intenciones — para reducir llamadas al LLM."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.domain.services.intent_classifier import Intent, IntentClassifier

router = APIRouter(prefix="/intent", tags=["intent"])


class ClassifyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000, description="Mensaje del usuario")


class ClassifyResponse(BaseModel):
    intent: str
    confidence: float
    endpoint: str | None
    requires_llm: bool


@router.post(
    "/classify",
    response_model=ClassifyResponse,
    summary="Clasificar intención del usuario sin LLM",
)
async def classify_intent(body: ClassifyRequest) -> ClassifyResponse:
    """Clasifica la intención del mensaje de texto usando regex.

    Si requires_llm es false: Ana ejecuta el endpoint indicado directamente.
    Si requires_llm es true: Ana debe procesar con el LLM.
    """
    intent, confidence = IntentClassifier.classify(body.text)
    endpoint = IntentClassifier.get_endpoint(intent)
    return ClassifyResponse(
        intent=intent.value,
        confidence=confidence,
        endpoint=endpoint,
        requires_llm=IntentClassifier.requires_llm(intent),
    )
