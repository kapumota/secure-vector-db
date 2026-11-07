### Integracion Merkle con flujos reales de escritura

#### Objetivo

La Fase 15.0 conecta la linea Merkle incremental con escrituras reales de SecureVectorDB.

El objetivo es que `insert` y `delete` puedan actualizar una raiz Merkle persistente, generar evidencia verificable y registrar auditoria JSONL.

#### Activacion

La integracion es opt-in para no cambiar el comportamiento por defecto.

```bash
export SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION=true
export SECURE_VECTOR_DB_MERKLE_WRITE_DB_PATH=secure-vector-db-merkle.sqlite
export SECURE_VECTOR_DB_MERKLE_WRITE_AUDIT_LOG=reports/merkle-write-audit.jsonl
```

#### Variables soportadas

```text
SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION
SECURE_VECTOR_DB_MERKLE_WRITE_DB_PATH
SECURE_VECTOR_DB_MERKLE_WRITE_AUDIT_LOG
```

Tambien se aceptan las variables previas:

```text
SECURE_VECTOR_DB_MERKLE_DB_PATH
SECURE_VECTOR_DB_MERKLE_AUDIT_LOG
```

#### Comportamiento

Cuando la integracion esta activa:

```text
insert -> actualiza hoja Merkle
delete -> elimina hoja Merkle
open   -> reconstruye Merkle desde registros persistidos
```

#### Evidencia

La evidencia se consulta usando la linea existente:

```text
SQLiteMerkleNodeStore
build_merkle_evidence_report
JsonlMerkleAuditLog
```

#### Garantia actual

Esta fase persiste hashes de hojas y nodos Merkle.

No persiste texto, vectores ni metadata privada dentro de las tablas Merkle.

#### Limite actual

La actualizacion Merkle ocurre despues de la escritura principal.

La transaccion atomica entre almacenamiento principal y almacenamiento Merkle queda para una fase posterior si se requiere aislamiento fuerte.

#### Criterio de aceptacion

```text
insert real cambia root Merkle
delete real cambia root Merkle
close/open recupera root Merkle
evidence report queda valid
auditoria JSONL registra eventos de escritura
```

#### Ruta posterior

```text
Fase 16.0 - API contract freeze y versionado
Fase 16.1 - Coverage uplift para release candidate
```

#### Correccion posterior a la auditoria

La apertura ya no reconstruye indiscriminadamente la evidencia Merkle auxiliar. Contrasta los hashes persistidos de hojas con los registros SQLite y conserva una discrepancia como fallo de integridad. Si no hay snapshot anterior, se permite un bootstrap inicial desde registros validados.

Las sustituciones de una hoja existente actualizan solo la hoja y su ruta a la raiz en la base auxiliar. Las inserciones y borrados siguen sujetos al costo de reconstruccion de su topologia.

La transaccion principal SQLite y el almacenamiento auxiliar Merkle siguen siendo archivos diferentes. El marcador `merkle_pending` sirve para diagnosticar interrupciones y bloquear escrituras, no garantiza un commit atomico entre ambas bases. Para protegerse frente a operadores maliciosos que falsifiquen ambos archivos se necesita un ancla de confianza externa.
