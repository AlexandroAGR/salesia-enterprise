"""Verificación end-to-end de la Fase 13 (Seguridad y auditoría).

Comprueba los seis bloques de la fase:

  1. Control de sesiones: tokens ausentes, corruptos o expirados.
  2. Matriz de roles y permisos sobre los endpoints protegidos.
  3. Registro de acciones críticas en audit_logs (RF-22) y
     consulta restringida al administrador con aislamiento por empresa.
  4. Validación de entrada (422) en formularios y consultas.
  5. Gestión segura de secretos (.env fuera de git, sin defaults).

Requisitos:
  - Backend corriendo en :8000 con seeds (runner SQLite o PostgreSQL).
    El seed debe incluir: admin@salesia.com (Administrador),
    gerente@otraempresa.com (Gerente), vendedor@salesia.com (Vendedor),
    analista@salesia.com (Analista), almacen@salesia.com (Almacén) y
    admin2@otraempresa.com (Administrador de la segunda empresa).
  - Ejecutarlo el ÚLTIMO de la cadena sobre una BD fresca:
    verify_fase12 → verify_fase11 → verify_fase10 → verify_fase09 →
    verify_fase08 → verify_fase13.

Uso:
  PYTHONPATH=$PWD .venv/bin/python verify_fase13.py
"""
from __future__ import annotations

import re
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import jwt

BACKEND_DIR = Path(__file__).resolve().parent
REPO_DIR = BACKEND_DIR.parent
BASE_URL = "http://localhost:8000"

USERS = {
    "Administrador": ("admin@salesia.com", "Admin123*"),
    "Gerente": ("gerente@otraempresa.com", "Gerente123*"),
    "Vendedor": ("vendedor@salesia.com", "Vendedor123*"),
    "Analista": ("analista@salesia.com", "Analista123*"),
    "Almacén": ("almacen@salesia.com", "Almacen123*"),
}
SECOND_ADMIN_EMAIL = "admin2@otraempresa.com"
SECOND_ADMIN_PASSWORD = "Admin123*"

ROLE_KEYS = ["Administrador", "Gerente", "Vendedor", "Analista", "Almacén"]

passed = 0
failed = 0


def check(label: str, condition: bool, extra: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {label}")
    else:
        failed += 1
        print(f"  ❌ {label}" + (f" → {extra}" if extra else ""))


def step(title: str) -> None:
    print(f"\n=== {title} ===")


def login(client: httpx.Client, email: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def me(client: httpx.Client, headers: dict) -> dict:
    response = client.get("/api/auth/me", headers=headers)
    response.raise_for_status()
    return response.json()


def audit_total(client: httpx.Client, headers: dict, **params) -> int:
    response = client.get(
        "/api/audit", headers=headers, params={**params, "page_size": 1}
    )
    if response.status_code != 200:
        return -1
    return response.json()["total"]


def request(
    client: httpx.Client,
    method: str,
    path: str,
    headers: dict | None,
    json=None,
):
    kwargs = {}
    if headers is not None:
        kwargs["headers"] = headers
    if json is not None:
        kwargs["json"] = json
    return client.request(method, path, **kwargs)


# --------------------------------------------------------------------
# Matriz de permisos: método, ruta, payload, estado esperado por rol
# --------------------------------------------------------------------
def build_probes(client: httpx.Client, headers: dict) -> list[tuple]:
    """Endpoints de prueba con los datos reales de la empresa.

    Los payloads de clientes y productos se construyen con una
    fábrica para que cada rol autorizado reciba un documento/SKU
    único (si no, el segundo creador recibiría 409).
    """
    customers = client.get(
        "/api/customers", headers=headers, params={"page_size": 1}
    ).json()
    products = client.get(
        "/api/products", headers=headers, params={"page_size": 1}
    ).json()

    customer_id = customers["items"][0]["id"] if customers["items"] else None
    product_id = products["items"][0]["id"] if products["items"] else None

    def customer_payload(role: str) -> dict:
        suffix = uuid.uuid4().hex[:8]
        return {
            "document_type": "DNI",
            "document_number": str(int(suffix, 16) % 10**8).zfill(8),
            "full_name": f"Cliente F13 {role}",
        }

    def product_payload(role: str) -> dict:
        return {
            "sku": f"F13-{uuid.uuid4().hex[:10].upper()}",
            "name": f"Producto F13 {role}",
            "unit_price": "10.00",
            "cost_price": "5.00",
        }

    ok = 200
    created = 201
    denied = 403
    missing = 404

    all_roles = {role: ok for role in ROLE_KEYS}

    return [
        # --- administración ---
        ("GET", "/api/audit", None, {"Administrador": ok, **{r: denied for r in ROLE_KEYS[1:]}}),
        # --- clientes ---
        ("GET", "/api/customers", None,
         {"Administrador": ok, "Gerente": ok, "Vendedor": ok,
          "Analista": denied, "Almacén": denied}),
        ("POST", "/api/customers", customer_payload,
         {"Administrador": created, "Gerente": denied, "Vendedor": created,
          "Analista": denied, "Almacén": denied}),
        # --- catálogo ---
        ("GET", "/api/products", None,
         {"Administrador": ok, "Gerente": ok, "Vendedor": ok,
          "Analista": denied, "Almacén": ok}),
        ("POST", "/api/products", product_payload,
         {"Administrador": created, "Gerente": denied, "Vendedor": denied,
          "Analista": denied, "Almacén": created}),
        ("GET", "/api/categories", None,
         {"Administrador": ok, "Gerente": ok, "Vendedor": ok,
          "Analista": denied, "Almacén": ok}),
        # --- inventario ---
        ("GET", "/api/inventory", None,
         {"Administrador": ok, "Gerente": ok, "Vendedor": ok,
          "Analista": denied, "Almacén": ok}),
        ("POST", "/api/inventory/movements",
         {"product_id": product_id, "movement_type": "entrada",
          "quantity": "1.000", "reason": "Verificación Fase 13"},
         {"Administrador": created, "Gerente": denied, "Vendedor": denied,
          "Analista": denied, "Almacén": created}),
        # --- pagos ---
        ("GET", "/api/payment-methods", None,
         {"Administrador": ok, "Gerente": ok, "Vendedor": ok,
          "Analista": denied, "Almacén": denied}),
        # --- ventas (lectura: todos; escritura: A y V) ---
        ("GET", "/api/sales", None, all_roles),
        ("POST", "/api/sales",
         {"customer_id": customer_id,
          "items": [{"product_id": product_id, "quantity": 1}]},
         {"Administrador": created, "Gerente": denied, "Vendedor": created,
          "Analista": denied, "Almacén": denied}),
        # --- analítica (lectura: todos, base del dashboard) ---
        ("GET", "/api/analytics/summary", None, all_roles),
        # --- insights / reportes / datasets / análisis ---
        ("GET", "/api/insights", None,
         {"Administrador": ok, "Gerente": ok, "Vendedor": denied,
          "Analista": ok, "Almacén": denied}),
        ("POST", "/api/insights/generate", {},
         {"Administrador": ok, "Gerente": ok, "Vendedor": denied,
          "Analista": ok, "Almacén": denied}),
        ("GET", "/api/reports", None,
         {"Administrador": ok, "Gerente": ok, "Vendedor": denied,
          "Analista": ok, "Almacén": denied}),
        ("POST", "/api/reports/generate",
         {"report_type": "ventas", "period": "all"},
         {"Administrador": created, "Gerente": created, "Vendedor": denied,
          "Analista": created, "Almacén": denied}),
        ("GET", "/api/datasets", None,
         {"Administrador": ok, "Gerente": ok, "Vendedor": denied,
          "Analista": ok, "Almacén": denied}),
        ("GET", "/api/analyses", None,
         {"Administrador": ok, "Gerente": ok, "Vendedor": denied,
          "Analista": ok, "Almacén": denied}),
        # El permiso se evalúa antes que el 404 del servicio: un rol
        # autorizado llega al servicio (404 por variable inexistente).
        ("POST", "/api/analyses/mean-median", {"variable_id": 999999},
         {"Administrador": missing, "Gerente": missing,
          "Vendedor": denied, "Analista": missing, "Almacén": denied}),
    ]


def main() -> int:
    global passed, failed

    with httpx.Client(base_url=BASE_URL, timeout=20.0) as client:
        health = client.get("/health")
        if health.status_code != 200:
            print("❌ El backend no responde en :8000")
            return 1

        tokens = {
            role: login(client, email, password)
            for role, (email, password) in USERS.items()
        }
        admin_headers = tokens["Administrador"]

        # ------------------------------------------------------------
        step("1. Control de sesiones")
        # ------------------------------------------------------------
        response = client.get("/api/customers")
        check(
            "Petición sin token → rechazada",
            response.status_code in (401, 403),
            str(response.status_code),
        )

        response = client.get(
            "/api/customers",
            headers={"Authorization": "Bearer token.basura.falso"},
        )
        check(
            "Token corrupto → 401",
            response.status_code == 401,
            str(response.status_code),
        )

        from app.core.config import settings

        now = datetime.now(timezone.utc)
        expired = jwt.encode(
            {
                "sub": "1",
                "exp": now - timedelta(minutes=5),
            },
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        response = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {expired}"}
        )
        check(
            "Token expirado → 401",
            response.status_code == 401,
            str(response.status_code),
        )

        forged = jwt.encode(
            {
                "sub": "1",
                "exp": now + timedelta(minutes=5),
            },
            "clave-secreta-diferente",
            algorithm=settings.jwt_algorithm,
        )
        response = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {forged}"}
        )
        check(
            "Token firmado con otra clave → 401",
            response.status_code == 401,
            str(response.status_code),
        )

        valid_token = admin_headers["Authorization"].split(" ", 1)[1]
        claims = jwt.decode(
            valid_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        ttl_minutes = (claims["exp"] - now.timestamp()) / 60
        check(
            "El JWT caduca en ≤ 60 minutos",
            0 < ttl_minutes <= 60.5,
            f"{ttl_minutes:.1f} min",
        )
        check(
            "El JWT declara exp (control de expiración)",
            "exp" in claims,
        )

        response = client.post("/api/auth/logout", headers=admin_headers)
        check(
            "Logout registrado con 204",
            response.status_code == 204,
            str(response.status_code),
        )

        # ------------------------------------------------------------
        step("2. Matriz de roles y permisos")
        # ------------------------------------------------------------
        admin_me = me(client, admin_headers)
        check(
            "/auth/me devuelve el nombre del rol",
            admin_me.get("role") == "Administrador",
            str(admin_me.get("role")),
        )
        probes = build_probes(client, admin_headers)

        audit_before = {
            action: audit_total(client, admin_headers, action=action)
            for action in (
                "customer.create",
                "product.create",
                "sale.create",
                "report.generate",
                "access.denied",
                "auth.login_failed",
            )
        }

        for method, path, payload, expected in probes:
            for role in ROLE_KEYS:
                body = payload(role) if callable(payload) else payload
                response = request(
                    client, method, path, tokens[role], json=body
                )
                want = expected[role]
                check(
                    f"{role}: {method} {path} → {want}",
                    response.status_code == want,
                    f"obtuvo {response.status_code}",
                )

        response = client.post(
            "/api/auth/login",
            json={"email": "admin@salesia.com", "password": "Incorrecta1*"},
        )
        check(
            "Login con contraseña incorrecta → 401",
            response.status_code == 401,
            str(response.status_code),
        )

        # ------------------------------------------------------------
        step("3. Registro de acciones críticas (RF-22)")
        # ------------------------------------------------------------
        audit_after = {
            action: audit_total(client, admin_headers, action=action)
            for action in audit_before
        }

        deltas = {
            "customer.create": 2,
            "product.create": 2,
            "sale.create": 2,
            # Sólo filas de esta empresa (Administrador + Analista);
            # la del Gerente queda en la auditoría de su empresa.
            "report.generate": 2,
            "access.denied": 1,
            "auth.login_failed": 1,
        }
        for action, minimum in deltas.items():
            delta = audit_after[action] - audit_before[action]
            check(
                f"'{action}' registró ≥ {minimum} acciones nuevas",
                delta >= minimum,
                f"delta={delta} ({audit_before[action]}→{audit_after[action]})",
            )

        logout_total = audit_total(
            client, admin_headers, action="auth.logout"
        )
        check(
            "'auth.logout' quedó registrado",
            logout_total >= 1,
            str(logout_total),
        )

        page = client.get(
            "/api/audit",
            headers=admin_headers,
            params={"action": "auth.login", "page_size": 50},
        ).json()
        admin_login = next(
            (
                item
                for item in page["items"]
                if item.get("details", {}).get("email")
                == "admin@salesia.com"
            ),
            None,
        )
        check(
            "El login guarda usuario, IP y correo en detalles",
            admin_login is not None
            and admin_login.get("user_name") == "Admin SalesIA"
            and admin_login.get("ip_address") == "127.0.0.1",
            str(admin_login),
        )

        filtered = client.get(
            "/api/audit",
            headers=admin_headers,
            params={"action": "sale.create", "page_size": 50},
        ).json()
        check(
            "El filtro por acción sólo devuelve esa acción",
            filtered["total"] > 0
            and all(
                item["action"] == "sale.create"
                for item in filtered["items"]
            ),
            str(filtered["total"]),
        )

        paged = client.get(
            "/api/audit",
            headers=admin_headers,
            params={"page": 1, "page_size": 3},
        ).json()
        check(
            "La auditoría pagina con page_size=3",
            len(paged["items"]) <= 3 and paged["total"] >= 3,
            f"{len(paged['items'])} items / total {paged['total']}",
        )

        # Aislamiento: el administrador de la otra empresa no ve nuestras filas
        second_headers = login(
            client, SECOND_ADMIN_EMAIL, SECOND_ADMIN_PASSWORD
        )
        second_me = me(client, second_headers)
        second_page = client.get(
            "/api/audit", headers=second_headers, params={"page_size": 100}
        ).json()

        check(
            "La generación del Gerente ajeno se audita en su empresa",
            audit_total(
                client, second_headers, action="report.generate"
            )
            >= 1,
        )

        our_latest = client.get(
            "/api/audit",
            headers=admin_headers,
            params={"action": "customer.create", "page_size": 1},
        ).json()["items"][0]

        check(
            "El administrador ajeno sólo ve auditoría de su empresa",
            all(
                item["company_id"] == second_me["company_id"]
                for item in second_page["items"]
            ),
            str({item["company_id"] for item in second_page["items"]}),
        )
        check(
            "Nuestras acciones críticas no se filtran a la otra empresa",
            our_latest["id"]
            not in {item["id"] for item in second_page["items"]},
            f"fila {our_latest['id']} filtrada",
        )

        # ------------------------------------------------------------
        step("4. Validación de entrada")
        # ------------------------------------------------------------
        invalid_cases = [
            (
                "Cliente con nombre demasiado corto → 422",
                "POST",
                "/api/customers",
                {"full_name": "A"},
            ),
            (
                "Cliente con correo inválido → 422",
                "POST",
                "/api/customers",
                {"full_name": "Nombre Completo", "email": "no-es-un-correo"},
            ),
            (
                "Venta sin detalles → 422",
                "POST",
                "/api/sales",
                {"items": []},
            ),
            (
                "Venta con cantidad no positiva → 422",
                "POST",
                "/api/sales",
                {"items": [{"product_id": 1, "quantity": 0}]},
            ),
            (
                "Producto con precio negativo → 422",
                "POST",
                "/api/products",
                {"sku": "F13-INVALID", "name": "Producto", "unit_price": -5},
            ),
            (
                "Login con correo inválido → 422",
                "POST",
                "/api/auth/login",
                {"email": "no-es-un-correo", "password": "x"},
            ),
        ]
        for label, method, path, payload in invalid_cases:
            response = request(
                client, method, path, admin_headers, json=payload
            )
            check(
                label,
                response.status_code == 422,
                str(response.status_code),
            )

        response = client.get(
            "/api/customers", headers=admin_headers, params={"search": ""}
        )
        check(
            "Búsqueda vacía (min_length) → 422",
            response.status_code == 422,
            str(response.status_code),
        )

        # ------------------------------------------------------------
        step("5. Gestión segura de secretos")
        # ------------------------------------------------------------
        root_gitignore = (REPO_DIR / ".gitignore").read_text(
            encoding="utf-8"
        )
        backend_gitignore = (BACKEND_DIR / ".gitignore").read_text(
            encoding="utf-8"
        )

        check(
            ".gitignore raíz excluye .env",
            any(
                line.strip().lstrip("/") == ".env"
                for line in root_gitignore.splitlines()
            ),
        )
        check(
            ".gitignore del backend excluye .env",
            any(
                line.strip().lstrip("﻿").lstrip("/") == ".env"
                for line in backend_gitignore.splitlines()
            ),
        )

        tracked = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        real_envs = [
            path
            for path in tracked
            if path == ".env" or path.endswith("/.env")
        ]
        check(
            "Ningún .env real está versionado",
            real_envs == [],
            str(real_envs),
        )
        check(
            ".env.example sí está versionado (plantilla pública)",
            "backend/.env.example" in tracked,
        )

        env_example = (BACKEND_DIR / ".env.example").read_text(
            encoding="utf-8"
        )
        example_secret = ""
        for line in env_example.splitlines():
            if line.startswith("JWT_SECRET_KEY="):
                example_secret = line.split("=", 1)[1].strip()
        check(
            "La plantilla usa un marcador de reemplazo",
            "REEMPLAZAR" in example_secret,
            example_secret,
        )

        env_file = BACKEND_DIR / ".env"
        env_secret = ""
        if env_file.exists():
            match = re.search(
                r"^JWT_SECRET_KEY=(.+)$",
                env_file.read_text(encoding="utf-8"),
                re.MULTILINE,
            )
            if match:
                env_secret = match.group(1).strip()

        check(
            "Existe un .env local con JWT_SECRET_KEY",
            env_secret != "",
        )
        check(
            "La plantilla no contiene el secreto real",
            example_secret != "" and example_secret != env_secret,
            f"plantilla={example_secret}",
        )

        config_source = (BACKEND_DIR / "app/core/config.py").read_text(
            encoding="utf-8"
        )
        check(
            "jwt_secret_key no tiene valor por defecto en config.py",
            re.search(r"jwt_secret_key:\s*str\s*=", config_source) is None,
        )
        check(
            "El algoritmo JWT es HS256",
            settings.jwt_algorithm == "HS256",
            settings.jwt_algorithm,
        )
        check(
            "El expiry configurado es de 60 minutos",
            settings.jwt_access_token_expire_minutes == 60,
            str(settings.jwt_access_token_expire_minutes),
        )

    print(f"\nRESULTADO FASE 13: {passed} ✅ / {failed} ❌")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
