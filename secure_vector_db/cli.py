from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

from secure_vector_db.database import SecureVectorDB
from secure_vector_db.errors import SecureVectorDBError

DEFAULT_DB_PATH = Path("secure_vector_db.sqlite")


def build_demo_db(path: Path | None = None, vector_index: str = "kd_tree", embedding_model: str = "hash", embedding_model_name: str | None = None) -> SecureVectorDB:
    db = SecureVectorDB.open(path, vector_index=vector_index, embedding_model=embedding_model, embedding_model_name=embedding_model_name) if path else SecureVectorDB(embedding_dim=8, vector_index=vector_index, embedding_model=embedding_model, embedding_model_name=embedding_model_name)
    if len(db.store) == 0:
        db.insert(1, "base de datos vectorial con arbol b plus", {"topic": "database"})
        db.insert(2, "criptografia con arbol de merkle para integridad", {"topic": "crypto"})
        db.insert(3, "busqueda de vecinos cercanos usando indices espaciales", {"topic": "indexing"})
        db.insert(4, "aprendizaje automatico y embeddings hash based de texto", {"topic": "ml"})
        db.insert(5, "sistemas distribuidos con replicacion y verificacion", {"topic": "distributed"})
    return db


def open_db(path: Path, vector_index: str = "kd_tree", embedding_model: str = "hash", embedding_model_name: str | None = None) -> SecureVectorDB:
    return SecureVectorDB.open(path, vector_index=vector_index, embedding_model=embedding_model, embedding_model_name=embedding_model_name)


def cmd_demo(args: argparse.Namespace) -> None:
    db = build_demo_db(args.db if args.persist else None, args.index, args.embedding, args.embedding_model_name)
    print("SecureVectorDB demo")
    print("Registros:", len(db.store))
    print("Root hash:", db.root_hash)
    print("Verificacion:", db.verify_dataset())
    print("Embedding:", db.embedder.name, getattr(db.embedder, "model_name", ""))
    print("Indice vectorial:", db.vector_index.backend_name)

    print("\nBusqueda por ID=2:")
    print(db.search_by_id(2))

    print("\nRango ID 2..4:")
    for rec in db.search_by_range(2, 4):
        print("-", rec.record_id, rec.text)

    print('\nBusqueda semantica: "integridad criptografica"')
    for rec, dist in db.semantic_search("integridad criptografica", k=3):
        print(f"- id={rec.record_id} dist={dist:.4f} text={rec.text}")

    if args.export_json:
        db.save(args.export_json)
        print(f"\nSnapshot JSON exportado en: {args.export_json}")
    if args.persist:
        print(f"\nBase SQLite persistente: {args.db}")
    db.close()


def cmd_insert(args: argparse.Namespace) -> None:
    db = open_db(args.db, args.index, args.embedding, args.embedding_model_name)
    metadata = {"source": "cli"} if args.topic is None else {"topic": args.topic}
    db.insert(args.id, args.text, metadata)
    print(f"Insertado id={args.id}. Registros={len(db.store)} Root={db.root_hash}")
    db.close()


def cmd_delete(args: argparse.Namespace) -> None:
    db = open_db(args.db, args.index, args.embedding, args.embedding_model_name)
    deleted = db.delete(args.id)
    print("Eliminado" if deleted else "No existia")
    print("Root hash:", db.root_hash)
    db.close()


def cmd_get(args: argparse.Namespace) -> None:
    db = open_db(args.db, args.index, args.embedding, args.embedding_model_name)
    rec = db.search_by_id(args.id)
    if rec is None:
        print(f"No encontrado: id={args.id}")
        sys.exit(2)
    print(rec)
    db.close()


def cmd_range(args: argparse.Namespace) -> None:
    db = open_db(args.db, args.index, args.embedding, args.embedding_model_name)
    for rec in db.search_by_range(args.start, args.end):
        print(f"{rec.record_id}\t{rec.text}\t{rec.metadata}")
    db.close()


def cmd_search(args: argparse.Namespace) -> None:
    db = open_db(args.db, args.index, args.embedding, args.embedding_model_name)
    for rec, dist in db.semantic_search(args.query, k=args.k):
        print(f"id={rec.record_id}\tdist={dist:.4f}\t{rec.text}")
    db.close()


def cmd_verify(args: argparse.Namespace) -> None:
    db = open_db(args.db, args.index, args.embedding, args.embedding_model_name)
    ok = db.verify_dataset()
    print("OK" if ok else "ALTERADO")
    print("Root hash:", db.root_hash)
    db.close()
    if not ok:
        sys.exit(3)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SecureVectorDB: base de datos vectorial verificable")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="ruta SQLite persistente")
    parser.add_argument("--index", choices=["kd_tree", "faiss", "hnsw", "auto"], default="kd_tree", help="backend de indice vectorial")
    parser.add_argument("--embedding", choices=["hash", "sentence_transformers", "auto"], default="hash", help="modelo de embeddings")
    parser.add_argument("--embedding-model-name", default=None, help="nombre Hugging Face para sentence-transformers")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("demo", help="ejecuta una demo completa")
    p.add_argument("--persist", action="store_true", help="guarda la demo en SQLite")
    p.add_argument("--export-json", type=Path, help="exporta snapshot JSON")
    p.set_defaults(func=cmd_demo)

    p = sub.add_parser("insert", help="inserta o reemplaza un documento persistente")
    p.add_argument("id", type=int)
    p.add_argument("text")
    p.add_argument("--topic")
    p.set_defaults(func=cmd_insert)

    p = sub.add_parser("delete", help="elimina un documento")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("get", help="busca por ID")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("range", help="busca por rango de IDs")
    p.add_argument("start", type=int)
    p.add_argument("end", type=int)
    p.set_defaults(func=cmd_range)

    p = sub.add_parser("search", help="busqueda semantica")
    p.add_argument("query")
    p.add_argument("-k", type=int, default=3)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("verify", help="verifica integridad Merkle")
    p.set_defaults(func=cmd_verify)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        args = parser.parse_args(["demo"])
    try:
        args.func(args)
    except SecureVectorDBError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
