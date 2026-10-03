#!/usr/bin/env python3
"""CLI de administración — Sonara (FastAPI). Reemplaza a manage.py de Django."""
import argparse
import getpass
import sys

from app.database import SessionLocal, init_db
from app.models import User
from app.security import hash_password


def cmd_initdb(_args):
    init_db()
    print("Base de datos inicializada.")


def cmd_createsuperuser(args):
    init_db()
    username = args.username or input("Usuario: ").strip()
    password = args.password or getpass.getpass("Contraseña: ")
    if len(password) < 8:
        print("La contraseña debe tener al menos 8 caracteres.", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == username).first():
            print(f"Ya existe un usuario «{username}».", file=sys.stderr)
            sys.exit(1)
        user = User(username=username, password_hash=hash_password(password), is_staff=True)
        db.add(user)
        db.commit()
        print(f"Superusuario «{username}» creado.")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Administración de Sonara")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("initdb", help="Crea las tablas de la base de datos").set_defaults(func=cmd_initdb)

    p_super = sub.add_parser("createsuperuser", help="Crea un usuario administrador")
    p_super.add_argument("--username")
    p_super.add_argument("--password")
    p_super.set_defaults(func=cmd_createsuperuser)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
