### Contrato publico de API

#### Objetivo

Este documento define el contrato publico de API para SecureVectorDB.

El objetivo es separar endpoints estables, endpoints de diagnostico y endpoints compatibles. Esto permite preparar releases sin prometer comportamiento que todavia es experimental.

#### Politica de estabilidad

```text
Los endpoints marcados como estable nucleo se consideran estables durante toda la serie 1.x.
estable durante toda la serie 1.x
Los endpoints marcados como estable diagnostico se consideran estables para observabilidad y depuracion durante la serie 1.x.
Los endpoints marcados como compatible se mantienen para no romper integraciones existentes, pero se recomienda usar la ruta nueva documentada.
Los cambios incompatibles deben reservarse para una version mayor.
```

#### Endpoints detectados

| Metodo | Ruta | Estado |
| --- | --- | --- |
| GET | `/explain/range` | estable diagnostico |
| GET | `/explain/records/{record_id}` | estable diagnostico |
| GET | `/health` | estable nucleo |
| GET | `/indexes/learned/health` | estable diagnostico |
| GET | `/indexes/ordered/explain/{record_id}` | compatible |
| GET | `/indexes/ordered/stats` | estable diagnostico |
| GET | `/persistence/health` | estable diagnostico |
| GET | `/range` | estable nucleo |
| POST | `/records` | estable nucleo |
| DELETE | `/records/{record_id}` | estable nucleo |
| GET | `/records/{record_id}` | estable nucleo |
| GET | `/search` | estable nucleo |
| GET | `/verify` | estable nucleo |
| POST | `/verify/assert` | estable nucleo |

#### Contrato de respuesta

Las respuestas JSON deben mantener nombres de campos estables dentro de la serie 1.x cuando el endpoint esta marcado como estable.

Los endpoints de diagnostico pueden agregar campos nuevos, pero no deben eliminar campos existentes sin documentarlo.

#### Autenticacion

Los endpoints protegidos deben requerir `X-API-Key` cuando la API se ejecuta con autenticacion habilitada.

Si falta una clave requerida o la clave no es valida, la respuesta debe usar estado HTTP `401`.

#### Errores

La politica de errores esta documentada en:

```text
docs/ERRORS.md
```

#### Compatibilidad

`/indexes/ordered/explain/{record_id}` se conserva como endpoint compatible. Para nuevas integraciones se recomienda:

```http
GET /explain/records/{record_id}
```

#### Alcance

Este contrato no promete replicacion, consenso, multi tenant enterprise ni compatibilidad distribuida.

SecureVectorDB se mantiene como base vectorial verificable y experimental, con contrato estable para su API publica local.
#### Relacion con storage

El contrato publico de API no expone todavia seleccion de backend persistente.

La Fase 10 prepara internamente `PersistentRecordStore`, pero SQLite sigue siendo el backend estable del release actual.
#### Relacion con AuthProvider

El contrato publico mantiene `X-API-Key` como mecanismo estable.

Internamente, la Fase 12.0 agrega `AuthProvider` y `ApiKeyAuthProvider` para preparar backends futuros sin cambiar endpoints ni respuestas publicas.
#### Politica de scopes

SecureVectorDB prepara scopes basicos para autorizacion gradual:

```text
read
write
admin
```

La politica de errores esperada es:

```text
401 -> autenticacion faltante o invalida
403 -> autenticacion valida pero scope insuficiente
```

El contrato publico mantiene `X-API-Key` como mecanismo estable mientras los endpoints migran gradualmente a dependencias con scope.
#### JWT experimental

El contrato publico mantiene `X-API-Key` como mecanismo estable.

`JWT experimental` queda disponible solo como backend opcional mediante:

```text
SECURE_VECTOR_DB_AUTH_BACKEND=jwt
```

El header esperado es:

```text
Authorization: Bearer <token>
```
#### Merkle incremental

La Fase 13.0 agrega un nucleo interno de Merkle incremental.

Esta fase no cambia endpoints ni respuestas publicas. La exposicion de metricas o pruebas Merkle por API queda fuera del alcance inmediato.
#### Persistencia Merkle interna

La Fase 13.1 agrega persistencia interna de Merkle incremental.

```text
docs/MERKLE_PERSISTENCE.md
```

Esta fase no cambia endpoints ni respuestas publicas. La exposicion de pruebas Merkle por API queda para una fase posterior.
