### Herramientas exploratorias controladas

Python >=3.10. Dependencias: requirements-dev.txt y requirements-ann.txt opcional, en un venv independiente. Ejecutar desde raiz, cada proceso usa un solo checkout.

```bash
python tools/controlled/greenann.py --source . --backend kd_tree --records 32 --queries 16
python tools/controlled/performance_gate.py baseline.json candidate.json
python tools/controlled/crash_oracle.py --source . --directory /tmp/caso-nuevo --phase after_commit
python tools/controlled/snapshot_audit.py /tmp/caso-nuevo/records.sqlite --sidecar /tmp/caso-nuevo/merkle.sqlite
python tools/controlled/pilot_runner.py config.json /tmp/piloto-nuevo
```

GreenANN reutiliza stats del benchmark existente. Corpus sintetico para smoke, sin energia ni recall. RSS incluye proceso completo y memoria nativa. Apertura y verificacion tienen una observacion por proceso.

La puerta recibe dos listas JSON de salidas GreenANN, >=5 pares, misma configuracion y entorno. Ejecutar AB/BA con hilos fijos. PASS no demuestra equivalencia. Intervalos bootstrap exploratorios por metrica sin correccion multiple, no garantizan inmunidad a carga compartida. Codigos PASS=0, FAIL=1, INCONCLUSIVE=2. Entradas invalidas fallan.

CrashOracle guarda history.jsonl con fsync en el padre. Permite una operacion sin reconocer. Puntos: before_commit, after_commit, after_return, after_ack. --operation insert prueba reemplazo, delete prueba borrado. Usa os._exit(86) sin close, no simula fallo de energia. Hook privado _durable.commit_record_and_root, verificar en otras versiones. PASS significa conformidad del historial, SnapshotAudit debe indicar FAIL si el auxiliar queda pendiente.

SnapshotAudit exige origen inactivo y formato v2. Lee con SQLite backup y abre solo copias temporales. Contrasta raiz, hojas/nodos, marcador, indices ID/rango y membresia vectorial reconstruida. No certifica recall ANN ni falsificacion coordinada. Pedir todos los vecinos es costoso, usar snapshots pequeños. Sin auxiliar explicito marca SKIP. No migra origen legacy. Copias de archivos separados no son atomicas.

Config piloto:
```json
{"mode":"exploratory","repeats":5,"backend":"kd_tree","records":32,"queries":16,"merkle":false,"variants":[{"name":"historica","path":"/ruta/checkout","commit":"SHA_COMPLETO"},{"name":"V3","path":null}]}
```

El autor debe mapear etiquetas historicas a commits. V3 ausente produce SKIP. mode=confirmatory se rechaza. Checkouts sin cambios versionados, el harness externo se ejecuta contra cada ruta. Interfaces historicas ausentes producen FAIL con stderr. results.json guarda variantes/runs, extraer arrays runs para la puerta. SHA de configuracion no equivale a protocolo cientifico congelado.

#### Clasificacion de controles negativos, parche 0006

Activar `"crash_audit": true` para ejecutar los ocho escenarios. Las expectativas se resuelven y guardan en `expectations.json`, con SHA-256 registrado en results.json, antes de iniciar GreenANN o cualquier escenario. No se infieren expectativas del resultado observado.

Cada variante puede seleccionar `recovery_expectation_profile`:

- `all-pass-v1`, predeterminado: exige PASS de ambos oraculos en los ocho escenarios. Un FAIL observado es UNEXPECTED_FAIL.
- `pr33-pending-merkle-v1`, explicito y valido solo para el commit `b18bcba268521668b1bf72314a136a2f095eee7f`: espera dos controles negativos after_commit (insert y delete). Exige historial PASS, snapshot FAIL, merkle_pending="1" en ambos resultados, recovery_marker=false y merkle_records=false. Todas las otras comprobaciones deben ser true, con auxiliar CHECKED y codigos de proceso correctos. No acepta fallos adicionales ni un PASS inesperado del control negativo.

Ejemplo para la base ya evaluada:

```json
{
  "mode": "exploratory",
  "repeats": 2,
  "records": 32,
  "queries": 16,
  "crash_audit": true,
  "variants": [
    {
      "name": "base-pr33",
      "path": "/ruta/checkout-base",
      "commit": "b18bcba268521668b1bf72314a136a2f095eee7f",
      "required": true,
      "recovery_expectation_profile": "pr33-pending-merkle-v1"
    },
    {"name": "V3", "path": null, "required": false}
  ]
}
```

Cada crash_audits conserva history y snapshot como JSON bruto, sin modificar sus estados. El campo execution guarda returncode, stdout y stderr separados, incluso ante errores o JSON invalido. El nuevo campo classification distingue PASS, EXPECTED_FAIL y UNEXPECTED_FAIL. Las variantes no disponibles conservan SKIP.

El status de variante ahora resume rendimiento y recuperacion. performance_status separa la evaluacion del rendimiento, coverage_status informa cobertura de escenarios. El estado global y exit_code se guardan en results.json: 0 si todas las ejecuciones coinciden con las expectativas, 1 por desviacion o perdida de cobertura, 2 por configuracion invalida o fallo previo a la ejecucion. Un EXPECTED_FAIL no cambia el FAIL bruto ni significa que el motor se haya recuperado.

Una variante con ruta tiene required=true por defecto. Una variante con path=null tiene required=false por defecto. Declarar required=true para que su ausencia obligue a salida no cero. Toda variante disponible debe completar todas sus repeticiones y los ocho escenarios si crash_audit=true, incluso si required=false. Un backend ausente, timeout, escenario perdido/duplicado, JSON invalido o resultado bruto incoherente nunca permite codigo 0. Si todas las variantes estan ausentes, no hay cobertura y la salida es no cero. Un perfil explicitamente seleccionado con crash_audit=false es invalido.

Cambio de formato de consumo: usar `classification` para la evaluacion de escenario y `performance_status` para rendimiento. El returncode se encuentra en execution.history o execution.snapshot, no se inyecta dentro del JSON bruto. Sin seleccionar explicitamente el perfil PR33, se mantiene el rechazo de los dos FAIL conocidos. No reutilizar el directorio de salida, no reinterpretar resultados anteriores para convertirlos en controles aceptados.
