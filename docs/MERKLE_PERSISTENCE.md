### Persistencia y recovery de Merkle incremental

#### Objetivo

La Fase 13.1 agrega persistencia y recovery para el nucleo `IncrementalMerkleTree`.

El objetivo es guardar hojas, nodos internos y raiz Merkle en SQLite, y poder recuperar el arbol despues de cerrar y abrir el proceso.

#### Componentes agregados

```text
SQLiteMerkleNodeStore
MerklePersistenceStats
MerkleRecoveryError
```

#### Tablas internas

```text
merkle_metadata
merkle_leaves
merkle_nodes
```

#### Recovery

El recovery reconstruye `IncrementalMerkleTree` desde hojas persistidas.

Si los nodos internos faltan pero las hojas y la raiz son consistentes, el sistema puede reconstruir los nodos internos.

#### Deteccion de corrupcion

La raiz persistida se compara contra la raiz reconstruida desde hojas.

Si no coincide, se reporta `MerkleRecoveryError`.

#### Alcance

Esta fase no cambia endpoints publicos.

La API publica para pruebas Merkle, auditoria externa o evidencia criptografica queda fuera del alcance inmediato.

#### Ruta posterior

```text
Fase 13.2 - API y evidencia Merkle verificable
```

#### Riesgo

Riesgo bajo-medio.

La persistencia se agrega como modulo interno sobre SQLite, sin modificar todavia el contrato publico de API.
