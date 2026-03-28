"""Servicio de inferencia de estrés desde HRV RMSSD.

Infiere el nivel de estrés (1-10) sin requerir input manual del usuario.
Modelo simplificado basado en literatura de HRV y ajustado para el perfil de Félix
(42 años, ~109 kg, actividad ligera).

Correlación inversa: HRV alto = estrés bajo, HRV bajo = estrés alto.
"""

from typing import Optional, Tuple


class StressInferenceService:
    """
    Mapeo HRV RMSSD → Estrés (1-10):
    - HRV > 60ms → estrés bajo (1-3)
    - HRV 40-60ms → estrés medio (4-6)
    - HRV 20-40ms → estrés alto (7-8)
    - HRV < 20ms → estrés muy alto (9-10)
    """

    @staticmethod
    def infer_from_hrv(hrv_rmssd: Optional[float]) -> Tuple[Optional[int], str]:
        """Retorna (stress_score, source).

        source = "inferred_hrv" si se calculó, "manual_required" si no hay HRV.
        stress_score es None si no se puede inferir.
        """
        if hrv_rmssd is None or hrv_rmssd <= 0:
            return (None, "manual_required")

        if hrv_rmssd > 60:
            # HRV alto: estrés bajo. Fórmula: inversamente proporcional.
            score = max(1, int(10 - (hrv_rmssd * 0.12)))
        elif hrv_rmssd > 40:
            # HRV moderado: estrés medio
            score = int(10 - (hrv_rmssd * 0.10))
        elif hrv_rmssd > 20:
            # HRV bajo: estrés alto
            score = int(10 - (hrv_rmssd * 0.075))
        else:
            # HRV muy bajo: estrés muy alto
            score = min(10, int(10 - (hrv_rmssd * 0.05)))

        score = max(1, min(10, score))
        return (score, "inferred_hrv")

    @staticmethod
    def stress_label(score: int) -> str:
        """Convierte un score numérico (1-10) en etiqueta legible."""
        if score <= 3:
            return "bajo"
        elif score <= 6:
            return "moderado"
        elif score <= 8:
            return "alto"
        return "muy_alto"
