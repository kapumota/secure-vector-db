"""Recuperacion restringida de confirmaciones Merkle coincidentes.

No reconstruye snapshots ni repara divergencias. Exige una raiz externa
verificada por el operador, un estado quiescente y un directorio de evidencias
nuevo. La aprobacion explicita es una confirmacion de operador, no un mecanismo
de autenticacion; la aplicacion anfitriona debe controlar el acceso.
"""

from __future__ import annotations

import hashlib
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import TYPE_CHECKING

from secure_vector_db.crypto.incremental_merkle import hash_leaf
from secure_vector_db.crypto.merkle_persistence import SQLiteMerkleNodeStore
from secure_vector_db.errors import IntegrityError

if TYPE_CHECKING:
    from secure_vector_db.database import SecureVectorDB


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _backup(source: sqlite3.Connection, dest: Path) -> None:
    """Respaldo consistente SQLite, compatible con bases en modo WAL."""
    with sqlite3.connect(dest) as target:
        source.backup(target)
    dest.chmod(0o600)
    handle = os.open(dest, os.O_RDONLY)
    try:
        os.fsync(handle)
    finally:
        os.close(handle)


def _durable_json(path: Path, payload: dict) -> None:
    """Guarda evidencia previa con reemplazo atomico y fsync."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("x", encoding="utf-8") as output:
        json.dump(payload, output, indent=2, sort_keys=True, ensure_ascii=False)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    temporary.chmod(0o600)
    temporary.replace(path)
    folder_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(folder_fd)
    finally:
        os.close(folder_fd)


def reconcile_matching_pending(
    db: "SecureVectorDB",
    *,
    trusted_root_hex: str,
    evidence_dir: str | Path,
    operator_id: str,
    approved: bool,
) -> dict[str, str]:
    """Confirma un pending SOLO si principal y auxiliar ya son coincidentes.

    Requiere mantenimiento exclusivo sin otros procesos escritores. La raiz
    recibida debe provenir de un registro externo confiable, no de esta BD.
    Ante divergencia, ausencia de evidencia o error, conserva el bloqueo.
    """
    if approved is not True or not isinstance(operator_id, str) or not operator_id.strip():
        raise IntegrityError("Se exige aprobacion explicita e identidad del operador")
    if not isinstance(trusted_root_hex, str) or not re.fullmatch(r"[0-9a-f]{64}", trusted_root_hex):
        raise IntegrityError("Se exige raiz SHA-256 hex de una referencia externa")
    primary = db._durable
    auxiliary = db._merkle_write_integrity
    if primary is None or auxiliary is None:
        raise IntegrityError("La recuperacion requiere SQLite principal y Merkle auxiliar activo")
    if primary.get_meta("merkle_pending", "0") != "1":
        raise IntegrityError("No existe una confirmacion pendiente recuperable")
    if primary.get_meta("root_format_version", "") != "2":
        raise IntegrityError("No se acepta migracion de formato durante recuperacion")

    persisted_records = primary.all()
    in_memory_records = db.store.all()
    expected_records = [r.canonical() for r in persisted_records]
    if expected_records != [r.canonical() for r in in_memory_records]:
        raise IntegrityError("La memoria no coincide con SQLite principal")
    # Importacion tardia para evitar ciclo con database.py.
    from secure_vector_db.database import SimpleMerkle
    calculated_root = SimpleMerkle.root_hex(expected_records)
    if not all((
        calculated_root == trusted_root_hex,
        primary.get_meta("root_hash", "") == trusted_root_hex,
        db._root_hash == trusted_root_hex,
        db._primary_merkle.root_hex == trusted_root_hex,
    )):
        raise IntegrityError("Raiz principal no coincide con la referencia externa")

    # Comprobar TODO el snapshot, no solamente el hash raiz.
    try:
        matches = (auxiliary.store.has_snapshot()
                   and auxiliary.matches_records(persisted_records)
                   and auxiliary.root_hex == trusted_root_hex
                   and auxiliary.store.load_root_hex() == trusted_root_hex)
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        raise IntegrityError("No se pudo verificar el Merkle auxiliar") from exc
    if not matches:
        raise IntegrityError("Merkle auxiliar divergente: recuperacion automatica prohibida")

    target = Path(evidence_dir).expanduser().resolve()
    target.mkdir(mode=0o700, parents=True, exist_ok=False)
    primary_backup = target / "principal_antes.sqlite"
    sidecar_backup = target / "auxiliar_antes.sqlite"
    manifest = target / "manifest.json"

    # Nunca reutilizar evidencia. No alterar pending antes de guardar backups.
    try:
        with primary._lock:
            _backup(primary.conn, primary_backup)
        with closing(sqlite3.connect(auxiliary.store.database_path)) as side_source:
            _backup(side_source, sidecar_backup)

        # Comprobar las copias, incluidas todas las hojas y nodos persistidos.
        with sqlite3.connect(primary_backup) as saved:
            pending = saved.execute(
                "SELECT value FROM kv_meta WHERE key='merkle_pending'"
            ).fetchone()
            root = saved.execute(
                "SELECT value FROM kv_meta WHERE key='root_hash'"
            ).fetchone()
        saved_aux = SQLiteMerkleNodeStore(sidecar_backup)
        correct_leaves = {
            r.record_id: hash_leaf(r.canonical()).hex() for r in persisted_records
        }
        if (pending != ("1",) or root != (trusted_root_hex,)
                or not saved_aux.verify_integrity()
                or saved_aux.load_root_hex() != trusted_root_hex
                or saved_aux.load_leaf_digests() != correct_leaves):
            raise IntegrityError("Las copias de evidencia no conservan el estado verificado")
        # Revalidar lo principal antes de completar la confirmacion.
        if (primary.get_meta("merkle_pending", "0") != "1"
                or primary.get_meta("root_hash", "") != trusted_root_hex
                or [r.canonical() for r in primary.all()] != expected_records
                or not auxiliary.matches_records(persisted_records)):
            raise IntegrityError("El estado cambio durante la preparacion de evidencia")
        _durable_json(manifest, {
            "status": "PREPARED_BEFORE_CONFIRMATION",
            "mode": "matching_pending_only",
            "operator_id": operator_id.strip(),
            "approved": True,
            "trusted_root_hex": trusted_root_hex,
            "root_format_version": "2",
            "primary_sha256": _digest(primary_backup),
            "sidecar_sha256": _digest(sidecar_backup),
            "record_count": len(persisted_records),
            "policy": "La raiz debe verificarse externamente; no se reparan divergencias",
        })
        # Persistir la decision antes del commit del marcador. Una interrupcion
        # posterior deja evidencia de la autorizacion y los respaldos previos.
        # Este archivo declara la INTENCION, no un resultado ya confirmado.
        _durable_json(target / "decision.json", {
            "status": "PREPARED_BEFORE_COMMIT",
            "operator_id": operator_id.strip(),
            "root_hex": trusted_root_hex,
            "manifest": "manifest.json",
            "manifest_sha256": _digest(manifest),
            "condition": "principal_y_auxiliar_coincidentes",
        })
        # El cambio del marcador es la ultima escritura obligatoria.
        # Nunca persistir un informe de exito despues de este commit: su fallo
        # podria dejar pending=0 pese a que la API informara error.
        primary.set_meta("merkle_pending", "0")
        db._integrity_compromised = False
        if not db.verify_dataset() or not auxiliary.matches_records(primary.all()):
            db._integrity_compromised = True
            try:
                primary.set_meta("merkle_pending", "1")
            except Exception:
                pass
            raise IntegrityError("Verificacion posterior fallida; bloquear escrituras")
        return {"status": "RECOVERED_MATCHING_PENDING", "evidence_dir": str(target),
                "root_hex": trusted_root_hex}
    except Exception:
        # Una excepcion no debe conceder permisos a un estado incierto.
        db._integrity_compromised = True
        raise
