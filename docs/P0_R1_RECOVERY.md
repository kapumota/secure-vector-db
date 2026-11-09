### SecureVectorDB: P0-R1.1, reconciliacion limitada de confirmacion pendiente

#### Alcance

Este cambio agrega `SecureVectorDB.recover_pending_merkle`, que SOLO completa
`merkle_pending=1` cuando SQLite principal y el snapshot Merkle auxiliar ya son
internamente validos, coinciden hoja por hoja y tienen la misma raiz confiable.
No repara divergencias ni reconstruye el Merkle auxiliar.

#### Contrato

- Requiere acceso exclusivo al archivo SQLite principal y al auxiliar. Ningun
  otro proceso puede escribirlos mientras se examinan, respaldan y confirman.
- Requiere `approved=True` e identificador no vacio del operador. Esto es
  consentimiento explicito, **NO autenticacion ni autorizacion criptografica**;
  el control de acceso se delega a la aplicacion que invoca el metodo.
- Requiere `trusted_root_hex` obtenido y verificado por un canal externo.
  **No es suficiente copiar `db.root_hash` o leer la propia SQLite afectada.**
- Requiere `root_format_version=2` y `merkle_pending=1`.
- Contrasta registros SQLite, memoria, cache principal, raiz persistida, raiz
  externa y snapshot auxiliar (hojas, nodos y raiz).
- Antes de modificar `merkle_pending`, crea un directorio nuevo y exclusivo con
  backups consistentes de cada SQLite (compatibles con WAL), SHA-256 y
  `manifest.json` duradero. No sobrescribe directorios existentes.
- Antes de completar el marcador persiste `decision.json`, que registra la
  intencion autorizada, el hash del manifiesto y el estado previo. No equivale
  a un comprobante de exito: el estado definitivo se confirma con una nueva
  lectura de `merkle_pending` y verificaciones integrales.
- No se escribe `resultado.json` despues de confirmar `merkle_pending=0`,
  para evitar una falla tardia que devuelva error con escrituras habilitadas.
- Solo pone `merkle_pending=0` cuando todas las comprobaciones coinciden.
- Ejecuta nueva verificacion al finalizar, sin saltarse `verify_dataset()`.
- Cualquier divergencia, evidencia insuficiente, fallo de backup o error en
  confirmacion bloquea la recuperacion.

#### Ejemplo para mantenimiento aislado

No ejecutar directamente sobre un servicio activo. El valor `RAIZ_EXTERNA`
debe obtenerse y autenticar desde evidencia confiable ajena al par de archivos
que se intenta recuperar.

```python
from secure_vector_db.database import SecureVectorDB

db = SecureVectorDB.open("/ruta/mantenimiento/registros.sqlite")
try:
    resultado = db.recover_pending_merkle(
        trusted_root_hex="RAIZ_EXTERNA_DE_64_DIGITOS_HEX",
        evidence_dir="/ruta/evidencias/recuperacion-20261109-01",
        operator_id="operador-autorizado",
        approved=True,
    )
    print(resultado)
finally:
    db.close()
```

La variable de entorno
`SECURE_VECTOR_DB_ENABLE_MERKLE_WRITE_INTEGRATION=true`
debe estar habilitada, y la ruta del auxiliar debe ser la misma usada antes del
fallo. Este metodo no es una API remota ni un sistema de roles.

#### Limitaciones que impiden declarar recuperacion general READY

1. Divergencia entre principal y auxiliar: permanece BLOCKED; necesita una
   decision sobre la autoridad de datos y evidencia externa autenticada.
2. Recuperacion ante corrupcion estructural del auxiliar: puede fallar antes de
   instanciar SecureVectorDB, por diseno fail-closed.
3. El almacenamiento principal y auxiliar no tienen una transaccion atomica
   conjunta; se exige mantenimiento exclusivo entre procesos.
4. El manifiesto registra SHA-256, pero no firma digitalmente la evidencia ni
   evita alteracion posterior por un operador con permisos de escritura.
5. Antes de cambiar el estado de P0-R1.1 a READY se deben ejecutar las pruebas
   nuevas y la suite completa en Python 3.10, 3.11 y 3.12, ademas de CI.

#### Pruebas agregadas

`tests/test_p0_matching_recovery.py` prueba recuperacion despues de reinicio,
rechazo sin aprobacion, raiz externa incorrecta, divergencia, alteracion
principal, fallo del commit del marcador, ausencia de escrituras de evidencia
posteriores al commit y fallo al persistir la decision previa.
