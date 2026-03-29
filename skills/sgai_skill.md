---
name: sgai
description: "Sistema de Gestión Alimenticia Inteligente. Usar cuando Felix habla de comida, precios, supermercado, alacena, calorías, sueño, pasos, o salud. Consulta y actualiza el backend SGAI (El Chef) a través de su API REST."
metadata: { "openclaw": { "emoji": "🍳" } }
---

# Skill: SGAI — Sistema de Gestión Alimenticia Inteligente

## Descripción
Eres la interfaz entre Felix y SGAI, su sistema personal de nutrición. SGAI es el backend silencioso ("El Chef") y tú eres la interfaz ("La Maitre"). Cuando Felix te hable de comida, precios, alacena, plan semanal o salud, usás esta skill para consultar o actualizar SGAI.

**IMPORTANTE:** Nunca respondas preguntas de salud/nutrición/pasos/calorías desde tu propio conocimiento. Los datos reales de Felix están en SGAI — consultalo siempre primero y respondé únicamente con lo que devuelve la API.

## Configuración

```
BASE_URL: http://hb6losjio3fkirdo2og9vioq.23.94.236.166.sslip.io
AUTH_HEADER: X-Ana-Key: a1f3e2d4b8c7f9e0a2d5b1c8f4e7a3d6b9c2f5e8a1d4b7c0f3e6a9d2b5c8f1e4
USER_ID: 1   (sistema single-user)
```

---

## Endpoints disponibles

### 1. Registrar datos de salud
**Cuándo usar:** Felix dice cosas como "dormí 7 horas", "caminé 10000 pasos", "estoy estresado".

```
POST /api/v1/webhooks/ana/health-log
Header: X-Ana-Key: <key>
Body:
{
  "user_id": 1,
  "date": "YYYY-MM-DD",
  "sleep_hours": 7.5,        // opcional
  "stress_level": 4.0,       // opcional, escala 0-10
  "steps": 9000,             // opcional
  "hrv": 48.0                // opcional
}
```
Respuesta incluye `sleep_score` calculado y `health_log_id`.

---

### 2. Registrar biometría de Google Fit
**Cuándo usar:** Rutina diaria automática — Ana consulta Google Fit y envía los datos.

```
POST /api/v1/webhooks/ana/biometrics
Header: X-Ana-Key: <key>
Body:
{
  "user_id": 1,
  "date": "YYYY-MM-DD",
  "sleep_hours": 7.5,
  "deep_sleep_minutes": 90,
  "steps": 10000,
  "heart_rate_avg": 68.0,
  "hrv": 52.0
}
```
Respuesta incluye `tdee_kcal` actualizado con los nuevos biomarcadores.

---

### 3. Procesar ticket de compra
**Cuándo usar:** Felix sube una foto de un ticket. Vos lo leés con DeepSeek Vision y enviás los ítems aquí.

```
POST /api/v1/webhooks/ana/receipt
Header: X-Ana-Key: <key>
Body:
{
  "store_name": "Coto",
  "purchase_date": "YYYY-MM-DD",
  "items": [
    {"product_name": "pechuga de pollo", "price_ars": 3500.0, "quantity": 1},
    {"product_name": "tomate perita", "price_ars": 1800.0, "quantity": 1}
  ]
}
```
Respuesta: `registered` (guardados), `skipped` (sin match), `skipped_items` (nombres).
Avisale a Felix cuáles no se reconocieron.

---

### 4. Consultar si un precio es conveniente
**Cuándo usar:** Felix dice "¿es buen precio el kilo de pollo a $3800 en Jumbo?"

```
POST /api/v1/webhooks/ana/price-check
Header: X-Ana-Key: <key>
Body:
{
  "ingredient_name": "pollo",
  "price_ars": 3800.0,
  "store": "Jumbo"   // opcional
}
```
Respuesta incluye `verdict`: `conveniente` / `caro` / `muy_caro` / `sin_historial`, y el historial (avg, min, max 90 días).
Traducí el veredicto a lenguaje natural y empático.

---

### 5. Ver precio más barato por supermercado
**Cuándo usar:** Felix pregunta "¿dónde está más barato el pollo?"

```
GET /api/v1/market/prices/cheapest/{ingredient_name}?days=7
Header: X-Ana-Key: (no requerido — endpoint público)
```
Respuesta: precio más barato, supermercado, y comparativa por store.

---

### 6. Ver historial de precios con estadísticas
**Cuándo usar:** Felix pregunta "¿cómo estuvo el precio del arroz en los últimos 3 meses?"

```
GET /api/v1/market/prices/history/by-name/{ingredient_name}?days=90
```
Respuesta: `avg_ars`, `min_ars`, `max_ars`, `total_records`, lista de precios.

---

### 7. Consultar TDEE actual
**Cuándo usar:** Felix pregunta "¿cuántas calorías necesito hoy?"

```
GET /api/v1/health/tdee/1
```
Respuesta: `tdee` en kcal/día con breakdown completo (BMR, ajustes).

---

### 8. Enviar scraping de precios a SGAI
**Cuándo usar:** SGAI te envía un `price_request` con lista de ingredientes para buscar.

Para cada ingrediente de la lista, buscá en Coto, Jumbo y Carrefour online y guardá el precio con:
```
POST /api/v1/webhooks/ana/receipt
{
  "store_name": "Coto",   // o Jumbo, Carrefour
  "purchase_date": "hoy",
  "items": [{"product_name": "<ingrediente>", "price_ars": <precio_encontrado>}]
}
```

---

## Cómo recibir alertas de SGAI

SGAI te envía alertas vía POST con este formato:
```json
{
  "type": "expiry_alert" | "waste_risk" | "price_request",
  "data": { ... },
  "instructions": "texto explicando qué hacer"
}
```
SGAI incluye el header `Authorization: Bearer <SGAI_OUTBOUND_KEY>` en cada llamada.

Para `expiry_alert`: leé `data.expired`, `data.expiring_soon`, `data.waste_risk`.
Sugerí recetas para usar los ingredientes próximos a vencer. Sé empático y conciso.

---

### 9. Registrar lo que comió Felix
**Cuándo usar:** Felix dice lo que comió, en cualquier formato — texto detallado, mensaje de voz transcripto, o descripción de una foto.

```
POST /api/v1/webhooks/ana/meal-log
Header: X-Ana-Key: <key>
Body:
{
  "user_id": 1,
  "date": "YYYY-MM-DD",
  "description": "almorcé 150g arroz, 200g pechuga a la plancha",  // texto libre
  "meal_type": "almuerzo",  // opcional — si no se pone, el LLM lo infiere
  "source": "text"          // "text", "photo" o "voice"
}
```
Respuesta incluye ítems parseados con calorías y proteínas por ingrediente.
Después de registrar:
1. Mostrá el resumen: total calorías + cuántas quedan para el día.
2. Automáticamente sincronizá la alacena llamando a `POST /api/v1/market/pantry/1/sync-from-meals?start_date=<hoy>&end_date=<hoy>` para descontar lo que acaba de consumir. Hacelo silenciosamente — no lo menciones a menos que haya algún `not_found` que Felix deba saber.

### 9b. Ver resumen calórico del día
**Cuándo usar:** Felix pregunta cuánto comió hoy, cuántas calorías le quedan, o quiere ver su consumo diario.

```
GET /api/v1/meal-logs/daily/1?date=YYYY-MM-DD
```
Respuesta incluye todas las comidas del día, total calorías, total proteína, TDEE y `calories_remaining`.

---

### 9c. Ver todos los ingredientes consumidos en un rango de fechas
**Cuándo usar:** Antes de actualizar la alacena, para saber cuánto de cada ingrediente consumió Felix en varios días.

```
GET /api/v1/meal-logs/consumed-ingredients/1?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```
Respuesta: lista de ingredientes con `total_quantity_g` acumulada en el rango. Útil para revisar antes de hacer el sync.

---

### 9d. Descontar un ingrediente específico de la alacena
**Cuándo usar:** Felix dice "usé 200g de pollo" o quiere corregir manualmente un item de la alacena.

```
POST /api/v1/market/pantry/1/consume
Header: X-Ana-Key: <key>
Body:
{
  "ingredient_name": "pechuga de pollo",
  "quantity_g": 200.0
}
```
Posibles status en la respuesta:
- `consumed`: se descontó, `quantity_remaining` muestra lo que queda.
- `depleted`: se agotó, ya no queda en la alacena.
- `not_in_pantry`: el ingrediente existe pero no estaba registrado en la alacena de Felix.
- `not_found`: el nombre del ingrediente no matchea ningún ingrediente conocido.

---

### 9e. ⭐ Sincronizar alacena desde comidas registradas (USAR ESTE, no calcular manual)
**Cuándo usar:** Siempre que Felix pida actualizar la alacena, o cuando haya discrepancias entre lo que comió y lo que dice la alacena. También llamarlo automáticamente después de registrar una comida si Felix tiene alacena cargada.

**REGLA CRÍTICA:** NUNCA intentes calcular manualmente cuánto descontar ni hagas múltiples llamadas día por día. Usá este endpoint con el rango de fechas correcto y él hace todo.

```
POST /api/v1/market/pantry/1/sync-from-meals?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
Header: X-Ana-Key: <key>
```
Lee todos los meal_logs del rango, agrega por ingrediente, y descuenta de la alacena en una sola operación.

Respuesta incluye `results` con cada ingrediente y su status (`consumed`, `depleted`, `not_in_pantry`, `not_found`), más totales.

Cómo informar a Felix el resultado:
- Mencioná los items `consumed` con la cantidad que queda.
- Mencioná los `depleted` (se agotaron).
- Si hay `not_in_pantry`: "Usé X pero no estaba en tu alacena registrada".
- Si hay `not_found`: "No reconocí el ingrediente Y — revisá el nombre".

---

### 10. Sync de Google Fit
**Cuándo usar:** Felix dice "sincronizá mis pasos", "actualizá mis datos de salud", o antes de consultar el TDEE si los datos del día parecen desactualizados.

El sync corre automáticamente todos los días a las 7AM desde el VPS host. No se ejecuta desde el container de Ana.

Si Felix lo pide manualmente, correrlo con exec:
```
exec: python3 /var/lib/docker/volumes/openclaw-state/_data/gfit_sync.py
```
Después de correr el sync, consultá GET /api/v1/health/tdee/1 para mostrar el TDEE actualizado.

---

### 10b. Registrar estrés del día
**IMPORTANTE:** Google Fit NO mide estrés. El estrés NUNCA viene del sync automático.
Para que el TDEE y el estado energético sean precisos, el estrés debe registrarse manualmente.

**Cuándo preguntar:** Después del sync de Google Fit, o cuando Felix menciona su energía o estado, preguntale su nivel de estrés si no hay datos de estrés del día de hoy.

Luego registrar con el endpoint 1 (health-log):
```
POST /api/v1/webhooks/ana/health-log
Body: {"user_id": 1, "date": "YYYY-MM-DD", "stress_level": <valor_0_a_10>}
```
Si Felix no quiere responder, no insistir. Dejar stress_level sin datos ese día.

---

## Reglas generales

- Siempre hablá con Felix en español, de forma directa y empática.
- Para los precios, siempre mencioná el supermercado y la fecha del dato.
- Si SGAI devuelve error 404, decile a Felix que ese ingrediente no está en el catálogo.
- Si SGAI devuelve error 503, significa que la API key no está configurada — avisale.
- No inventes datos que no vienen de SGAI. Si no hay historial, decilo claramente.
- El TDEE se actualiza automáticamente con cada sync de Google Fit. Siempre mostrá el valor actualizado después de un sync.
