### Persistencia y recuperacion

#### Objetivo

La Fase 7 valida que SecureVectorDB pueda cerrar, reabrir y reconstruir sus indices auxiliares desde SQLite sin perder integridad.

Esta fase no agrega un algoritmo nuevo. Refuerza la confiabilidad del sistema para que SQLite sea tratado como fuente durable de verdad.

#### Componentes cubiertos

```text
SQLite
B+ Tree
indice vectorial
Merkle root
learned index persistido
metadata auxiliar
explain plan
```

#### Politica de recuperacion

El sistema debe poder reconstruir indices auxiliares desde los registros persistidos en SQLite.

```text
- SQLite records es la fuente durable de verdad.
- B+ Tree se reconstruye desde records al abrir la base.
- El indice vectorial se reconstruye desde embeddings persistidos.
- El Merkle root se compara contra la raiz calculada.
- El learned index solo se activa si su metadata y segmentos son validos.
- Si la metadata del learned index no es valida, la busqueda exacta sigue por B+ Tree.
```

#### Diagnostico

CLI:

```bash
python -m secure_vector_db.cli --db demo.sqlite persistence-health
```

API:

```http
GET /persistence/health
```

Campos principales:

```text
status
reason
durable_enabled
record_count
root_hash
computed_root_hash
persisted_root_hash
root_matches
recoverable_indexes
source_of_truth
learned_index
```

#### Estados

```text
healthy
memory_only
needs_recovery
```

#### Evidencia de pruebas

La fase agrega pruebas para:

```text
- insertar datos, cerrar, reabrir y consultar;
- borrar datos, cerrar, reabrir y verificar Merkle root;
- entrenar learned index, cerrar, reabrir y conservar segmentos;
- detectar metadata incompatible del learned index;
- reconstruir B+ Tree e indice vectorial desde SQLite;
- manejar base vacia;
- manejar reemplazo de registros sin duplicados.
```

#### Alcance

Esta fase no implementa backups, migraciones versionadas ni reparacion automatica destructiva.

La recuperacion es conservadora: diagnostica inconsistencias y mantiene busqueda exacta por B+ Tree cuando el learned index no puede activarse.

#### Correccion posterior a la auditoria (formato v2)

La raiz principal usa ahora representacion canonica JSON versionada y prefijos de dominio para hojas y nodos. La escritura de registros y raiz principal se confirma dentro de una unica transaccion SQLite.

Si una base antigua presenta raiz persistida no coincidente, el sistema indica `needs_recovery` y rechaza nuevas escrituras. No reconstituye automaticamente una raiz de confianza. La migracion de bases legacy que contienen un snapshot Merkle auxiliar requiere un procedimiento separado y supervisado con backup.

Cuando el Merkle de escrituras reales esta habilitado en una base independiente, el campo `merkle_pending=1` indica que una escritura principal pudo confirmarse sin sincronizacion de la evidencia auxiliar. No reabrir para escrituras hasta una reconciliacion controlada. Esta marca **no proporciona atomicidad entre archivos SQLite**.
