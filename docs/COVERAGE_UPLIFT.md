### Coverage uplift para release inicial

#### Objetivo

La Fase 16.1 sube la cobertura real hasta cumplir el umbral de release inicial.

El objetivo es mantener el umbral en 80 por ciento y agregar pruebas utiles sobre comportamiento existente.

#### Criterio principal

```bash
make coverage-strict
```

Debe terminar con codigo cero.

#### Validacion de release inicial

```bash
make release-initial-check
```

Este target ejecuta la validacion completa base y exige cobertura estricta.

#### Areas cubiertas

Las pruebas agregadas cubren:

```text
Record y RecordStore
KDTreeVectorIndex
factory de indices
HashEmbeddingModel
SecureVectorDB snapshot e integridad
persistencia SQLite
SimpleMerkle
CLI local
```

#### Politica

No se baja el umbral de cobertura.

No se agregan pruebas artificiales sobre detalles sin valor de producto.

No se cambian endpoints ni contrato publico.

#### Ruta posterior

```text
Fase 17.0 - Release candidate v1.0.0-rc1
```
#### Refuerzo 16.1.2

Se agregan pruebas adicionales para aumentar cobertura real sin modificar el umbral.

Areas reforzadas:

```text
B+ Tree
learned index
learned index health
explain plan
auth provider
auth scopes
rate limit
Merkle write integration
```
#### Refuerzo 16.1.3

Se agregan pruebas finales de cobertura sobre rutas estables y de bajo riesgo.

Areas reforzadas:

```text
LinearVectorIndex
RecordStore
store factory
HashEmbeddingModel
SecureVectorDB open
Merkle write env
```
