### Integracion productiva y auditoria Merkle

#### Objetivo

La Fase 13.3 integra la evidencia Merkle en una ruta productiva controlada.

La fase completa la linea de integridad verificable:

```text
nucleo incremental
persistencia
recovery
evidencia
auditoria Merkle
```

#### Componentes agregados

```text
MerkleAuditEvent
JsonlMerkleAuditLog
create_protected_merkle_evidence_router()
install_merkle_evidence_routes()
install_merkle_evidence_routes_from_env()
run_merkle_evidence_cli()
```

#### Activacion productiva

La API Merkle no se habilita por defecto.

```bash
SECURE_VECTOR_DB_ENABLE_MERKLE_API=true
SECURE_VECTOR_DB_MERKLE_DB_PATH=secure-vector-db-merkle.sqlite
SECURE_VECTOR_DB_MERKLE_AUDIT_LOG=reports/merkle-audit.jsonl
```

#### Permisos recomendados

```text
GET /merkle/root     -> read
GET /merkle/verify   -> admin
GET /merkle/evidence -> admin
```

#### CLI interna

Comandos equivalentes:

```text
merkle-root
merkle-verify
merkle-evidence
```

En esta fase se agrega `secure_vector_db.cli.merkle_evidence` y el wrapper `scripts/merkle_evidence.py`.

#### Auditoria

Cada consulta de evidencia puede registrar un evento JSONL con:

```text
action
status
root_hex
leaf_count
node_count
message
timestamp_unix
```

No se registran vectores, payloads, metadatos privados ni digests por registro.

#### Ruta posterior

```text
Fase 14 - Evidence Pack y release hardening
```
#### Fase 14.0 - Evidence Pack

La evidencia Merkle y auditoria alimentan el evidence pack de release.

```text
docs/RELEASE_EVIDENCE.md
```
