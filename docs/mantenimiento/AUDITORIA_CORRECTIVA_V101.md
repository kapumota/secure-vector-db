### SecureVectorDB: resultados de la correccion correctiva sobre 9e8ec85a33dd

#### Alcance del parche

Este parche se genero exclusivamente a partir del ZIP del commit `9e8ec85a33dd`, sin acceso al repositorio remoto del autor. Es un **candidato de mantenimiento para evaluacion**, no una version publicada ni una certificacion criptografica.

#### Defectos abordados

| Hallazgo | Intervencion | Cobertura |
|---|---|---|
| H1, capacidad HNSW | Cuenta slots fisicos y reconstruye cuando hay tombstones. Reutilizacion de IDs marcada mediante reconstruccion | Regresiones con backend simulado, prueba optativa con hnswlib real |
| H2, canonicalizacion | JSON canonico versionado, orden recursivo, normalizacion previa a persistir y floats exactos (`float.hex()`) | Reinicio con metadata anidada e IDs JSON, precision de embeddings, migracion legacy |
| H3, Merkle offline | Compara hojas persistidas con los registros reales antes de operar. No sobreescribe automaticamente las hojas existentes | Alteracion offline, raiz principal forjada, bloqueo de escrituras |
| H4, atomicidad | Registro y raiz principal se guardan en una transaccion de **la misma base SQLite**. La base Merkle separada utiliza marcador duradero de operacion pendiente y bloquea escrituras ante fallos | Trigger SQLite y fallo Merkle simulado |
| H5, costo de escritura | Al reemplazar una hoja Merkle existente, solo actualiza la hoja y los ancestros en la base Merkle | Prueba que impide guardar el arbol completo en un reemplazo |
| H6, autenticacion y salud | Scopes usan la politica de API key cerrada de `auth.py`. `/health` devuelve solo estado general | Credenciales de desarrollo no autorizadas, HTTP 401, respuesta publica minima |
| H7, Merkle legado | SHA-256 por defecto, separacion de dominio y prueba de una sola hoja sin error de indice | Regresion de digest y demostracion unitaria |
| H8, cobertura CI | Job optativo con instalacion real de FAISS/HNSW en Python 3.11 | Smoke y pruebas reales, pendientes de ejecutar en GitHub Actions del autor |

#### Garantias y limitaciones importantes

**No hay atomicidad global entre dos archivos SQLite independientes.** El registro principal y `root_hash` ahora se confirman juntos. Si la base Merkle auxiliar falla despues, se conserva `merkle_pending=1`, se deshabilitan las escrituras y se exige reconciliacion controlada. Una interrupcion entre ambas bases puede dejar una operacion principal confirmada aunque el cliente haya recibido un error. El marcador no convierte la operacion en un commit distribuido.

**No se detecta un adversario que pueda falsificar todas las evidencias locales.** Un operador que controle SQLite principal, la base Merkle auxiliar y sus metadatos puede reemplazar coherentemente datos y raices. Para resistencia a manipulacion coordinada, rollback y borrado verificable hace falta una raiz autenticada externamente, contador monotono confiable, registro de transparencia o mecanismo equivalente. El parche no afirma resolver ese modelo de amenazas.

**El costo total por escritura no es O(log n).** El reemplazo de hoja existente en la base Merkle evita su reescritura completa. La comprobacion/recomputacion del hash principal sigue siendo O(n), y las inserciones/borrados que cambian la topologia del arbol Merkle vuelven a reconstruirlo. No extrapolar las mejoras del reemplazo a millones de registros.

**Cambio de formato persistente.** Se introduce `root_format_version=2` con canonicalizacion JSON y separacion de dominios para la raiz principal. Si una base heredada contiene una raiz legacy que coincide con la recomputada desde sus registros, sin snapshot Merkle separado, la primera apertura migra la raiz principal a v2. Cuando la evidencia legacy no coincide, se bloquean escrituras y no se corrige silenciosamente. Si existe un snapshot Merkle auxiliar legado, la migracion debe realizarse como procedimiento supervisado con backups: no se realiza de forma automatica entre dos bases.

**Compatibilidad de clientes.** El endpoint publico `GET /health` pasa a responder exclusivamente `{"status":"ok"}`. Los metadatos operativos deben consultarse en endpoints autenticados. Si hay clientes que dependan de los campos antiguos, este cambio es incompatible y debe documentarse antes de una release `v1.0.1`.

**MerkleTree legado.** Cambia su algoritmo por defecto para hojas/nodos, por lo que los hashes previos de ese componente experimental no son compatibles. No se utiliza como raiz persistente de SecureVectorDB. No se declara un nuevo protocolo criptografico auditado.

**Datos anteriores y auditoria.** Las campañas G0/G0.1/P0 siguen congeladas. Este parche no recalcula ni altera sus artefactos. No se recomienda utilizar bases productivas existentes para probar la migracion sin copia verificable de cada base y sus archivos auxiliares.

#### Verificacion local del parche

Se ejecutan los tests contra una copia aislada. El entorno del parche puede no disponer de hnswlib o FAISS; esos tests son optativos localmente y deberian ejecutarse con implementaciones reales en la CI del autor. Es obligatorio comprobar tambien las pruebas bajo Python 3.10 antes de publicar una release.

#### Criterios pendientes para un release

- Pruebas completas y nuevos tests con Python 3.10 en la maquina del autor.
- Ejecuciones reales HNSW y FAISS y verificacion de CI.
- Ensayo supervisado de migracion con copias de bases SQLite existentes.
- Decidir si el cambio de `/health` y del formato persistente exige version mayor.
- Diseñar, fuera de este parche, una solucion transaccional global y un ancla de confianza externa si se quieren prometer esas garantias.

#### Separacion de la investigacion cientifica

Estas correcciones son mantenimiento de software; **no constituyen por si mismas un resultado cientifico original** ni alteran el dictamen NO GO de P0. Work debe evaluar nuevas contribuciones con la evidencia y los limites descritos, sin reutilizar defectos corregidos como supuestas novedades.
