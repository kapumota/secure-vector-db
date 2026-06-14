### Merkle incremental interno

#### Objetivo

La Fase 13.0 agrega `IncrementalMerkleTree` como nucleo interno para evolucionar la integridad verificable de SecureVectorDB.

El objetivo es reducir el costo de recalcular la raiz Merkle cuando cambia una hoja existente, preparando una ruta hacia persistencia y recovery en una fase posterior.

#### Componentes agregados

```text
IncrementalMerkleTree
MerkleNodeDigest
MerkleUpdateResult
compute_merkle_root_hex()
hash_leaf()
hash_pair()
```

#### Modos de actualizacion

```text
path    -> se actualiza una hoja existente y se recalcula solo la ruta a la raiz
rebuild -> cambia la forma del arbol por insercion o eliminacion
noop    -> no hubo cambio efectivo
```

#### Garantia de consistencia

La raiz incremental debe coincidir con la raiz calculada desde cero usando las mismas hojas ordenadas por `record_id`.

Esta fase agrega pruebas para:

```text
insert
delete
update
noop
comparacion contra reconstruccion completa
```

#### Limites de Fase 13.0

Esta fase no persiste nodos Merkle.

Las inserciones y eliminaciones reconstruyen la forma interna del arbol porque cambian la cantidad de hojas. La persistencia de nodos y recovery incremental quedan para Fase 13.1.

#### Ruta posterior

```text
Fase 13.1 - Persistencia y recovery de Merkle incremental
```

#### Riesgo

Riesgo bajo.

La fase agrega un modulo interno y pruebas, sin reemplazar todavia el flujo publico de persistencia. Esto permite validar el nucleo incremental antes de acoplarlo al storage durable.
#### Fase 13.1 - Persistencia y recovery

La persistencia y recovery del arbol incremental se documenta en:

```text
docs/MERKLE_PERSISTENCE.md
```
