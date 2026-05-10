---
name: Stats module - decisiones de implementación
description: Decisiones finales del módulo de estadísticas de reservas Autocab
type: project
---

Módulo `/stats/bookings/summary` completado.

**Why:** Los números no cuadraban con la base de datos directa por timezone mismatch entre la conexión Python (UTC por defecto) y la sesión del cliente SQL (America/Mexico_City).

**Decisiones finales:**
- Campo de fecha: `archive_time` (cuándo fue completada/cancelada), no `pickup_due_time`
- Timezone de conexión Autocab: `America/Mexico_City`, configurado con event listener `checkout` en `database.py`
- Rango de fechas: `>= dt_from AND < dt_to` (no BETWEEN), con `dt_to = medianoche del día siguiente`
- El event listener usa `checkout` (no `connect`) para garantizar el timezone en cada consulta, incluyendo conexiones reutilizadas del pool

**How to apply:** Si se agregan nuevos endpoints que consulten la BD de Autocab con fechas, usar siempre `archive_time` para filtrar completadas/canceladas, y tener en cuenta que el timezone ya está configurado globalmente en el engine.
