# Tabla: public.bookings (Autocab DB)

Base de datos externa de Autocab. Solo lectura desde este proyecto.

## Campos de fecha clave

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `pickup_due_time` | timestamptz NOT NULL | Cuándo está programada la recogida (indexed) |
| `booked_at_time` | timestamptz NOT NULL | Cuándo se creó la reserva (indexed) |
| `archive_time` | timestamptz NULL | Cuándo fue archivada (completada o cancelada) |
| `dispatched_at_time` | timestamptz NULL | Cuándo se despachó al conductor |
| `vehicle_arrived_at_time` | timestamptz NULL | Cuándo llegó el vehículo |
| `picked_up_at_time` | timestamptz NULL | Cuándo se recogió al pasajero |
| `completed_at_time` | timestamptz NULL | Cuándo se completó la reserva |
| `created_at` | timestamptz | Timestamp interno de inserción en la réplica |
| `updated_at` | timestamptz | Timestamp interno de actualización en la réplica |

## Campo de estado

- `archive_reason` varchar(50): `'Completed'` | `'Cancelled'` | otros
- Índice: `idx_archive_reason`

## Para stats de completadas/canceladas

Usar `archive_time` como campo de filtro de fecha — es cuando la reserva llegó a su estado final.
**No usar `pickup_due_time`** para este caso: agrupa por cuándo estaba programada, no por cuándo ocurrió.

## DDL completo

```sql
CREATE TABLE public.bookings (
    id int8 NOT NULL,
    pickup_due_time timestamptz NOT NULL,
    booked_at_time timestamptz NOT NULL,
    pickup_zone_id int4 NULL,
    pickup_zone_name varchar(255) NULL,
    pickup_address text NULL,
    pickup_street text NULL,
    pickup_latitude numeric(10, 8) NULL,
    pickup_longitude numeric(11, 8) NULL,
    pickup_note text NULL,
    destination_zone_id int4 NULL,
    destination_zone_name varchar(255) NULL,
    destination_address text NULL,
    destination_street text NULL,
    destination_latitude numeric(10, 8) NULL,
    destination_longitude numeric(11, 8) NULL,
    customer_name varchar(255) NULL,
    telephone_number varchar(50) NOT NULL,
    capabilities _int4 NULL,
    rejected_vehicles _int4 NULL,
    booking_source varchar(50) NULL,
    fare numeric(15, 2) NULL,
    cost numeric(15, 2) NULL,
    price numeric(15, 2) NULL,
    pricing_tariff varchar(100) NULL,
    meter_distance_km numeric(15, 3) NULL,
    gps_meter_distance_km numeric(15, 3) NULL,
    gps_meter_price numeric(15, 2) NULL,
    pricing_source varchar(50) NULL,
    requested_drivers _int4 NULL,
    forbidden_drivers _int4 NULL,
    requested_vehicles _int4 NULL,
    forbidden_vehicles _int4 NULL,
    archive_time timestamptz NULL,
    original_auto_id int8 NULL,
    archive_reason varchar(50) NULL,
    driver_id int4 NULL,
    driver_callsign varchar(50) NULL,
    driver_full_name varchar(255) NULL,
    vehicle_id int4 NULL,
    vehicle_callsign varchar(50) NULL,
    picked_up_at_time timestamptz NULL,
    dispatched_at_time timestamptz NULL,
    completed_at_time timestamptz NULL,
    vehicle_arrived_at_time timestamptz NULL,
    badge_number varchar(50) NULL,
    reg_number varchar(50) NULL,
    dispatch_source varchar(50) NULL,
    system_distance_km numeric(15, 3) NULL,
    was_exchanged bool NULL,
    estimated_time_seconds int4 NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NULL,
    updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NULL,
    CONSTRAINT bookings_pkey PRIMARY KEY (id)
);
```

## Índices

```sql
CREATE INDEX idx_archive_reason ON public.bookings USING btree (archive_reason);
CREATE INDEX idx_booked_at_time ON public.bookings USING btree (booked_at_time);
CREATE INDEX idx_pickup_due_time ON public.bookings USING btree (pickup_due_time);
CREATE INDEX idx_destination_zone_name ON public.bookings USING btree (destination_zone_name);
CREATE INDEX idx_driver_id ON public.bookings USING btree (driver_id);
CREATE INDEX idx_pickup_zone_name ON public.bookings USING btree (pickup_zone_name);
CREATE INDEX idx_telephone_number ON public.bookings USING btree (telephone_number);
CREATE INDEX idx_vehicle_id ON public.bookings USING btree (vehicle_id);
```
