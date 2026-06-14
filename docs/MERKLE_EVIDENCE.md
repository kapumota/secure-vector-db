### API y evidencia Merkle verificable

#### Objetivo

La Fase 13.2 completa la linea de integridad verificable de SecureVectorDB.

Esta fase conecta el nucleo incremental, la persistencia, el recovery y la evidencia exportable.

#### Componentes agregados

```text
MerkleEvidenceReport
build_merkle_evidence_report()
verify_merkle_evidence()
export_merkle_evidence_json()
create_merkle_evidence_router()
```

#### Estados de evidencia

```text
valid
corrupted
missing_nodes
recovered
empty
```

#### API opcional

La fase agrega un router reutilizable para FastAPI:

```text
GET /merkle/root
GET /merkle/verify
GET /merkle/evidence
```

El router se crea con:

```python
from secure_vector_db.api.merkle_evidence import create_merkle_evidence_router
```

#### Reporte JSON

`MerkleEvidenceReport` expone solo informacion segura:

```text
status
root_hex
leaf_count
node_count
recovered_from
algorithm
storage_backend
evidence_version
message
```

No expone vectores, payloads, metadatos privados ni digests por registro.

#### Recovery

`/merkle/evidence?recover_missing_nodes=true` puede reconstruir nodos internos cuando las hojas y la raiz persistida son consistentes.

#### Alcance

Esta fase no fuerza la integracion en `server.py`.

La integracion productiva del router debe hacerse de forma explicita cuando se definan politicas de autenticacion y despliegue.

#### Ruta posterior

```text
Fase 13.3 - Integracion productiva y auditoria Merkle
```
#### Fase 13.3 - Integracion productiva y auditoria

La integracion productiva y auditoria Merkle se documenta en:

```text
docs/MERKLE_AUDIT.md
```
