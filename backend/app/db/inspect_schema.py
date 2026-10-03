
from sqlalchemy import inspect

from app.db.session import engine


def main() -> None:
    inspector = inspect(engine)

    with engine.connect() as connection:
        database_name = connection.exec_driver_sql(
            "SELECT current_database()"
        ).scalar_one()

        postgres_version = connection.exec_driver_sql(
            "SELECT version()"
        ).scalar_one()

    print("=" * 72)
    print("INSPECCIÓN DEL ESQUEMA - SALESIA ENTERPRISE")
    print("=" * 72)
    print(f"Base de datos: {database_name}")
    print(f"Servidor: {postgres_version}")
    print()

    schemas = inspector.get_schema_names()

    for schema in ("public",):
        if schema not in schemas:
            continue

        tables = inspector.get_table_names(schema=schema)
        views = inspector.get_view_names(schema=schema)

        print(f"ESQUEMA: {schema}")
        print(f"Tablas encontradas: {len(tables)}")
        print()

        for table_name in tables:
            print(f"--- TABLA: {schema}.{table_name} ---")

            for column in inspector.get_columns(
                table_name, schema=schema
            ):
                nullable = "NULL" if column["nullable"] else "NOT NULL"
                default = column.get("default")

                print(
                    f"  COLUMNA: {column['name']} | "
                    f"TIPO: {column['type']} | "
                    f"{nullable} | DEFAULT: {default}"
                )

            primary_key = inspector.get_pk_constraint(
                table_name, schema=schema
            )
            print(f"  CLAVE PRIMARIA: {primary_key}")

            for fk in inspector.get_foreign_keys(
                table_name, schema=schema
            ):
                print(f"  CLAVE FORÁNEA: {fk}")

            for unique in inspector.get_unique_constraints(
                table_name, schema=schema
            ):
                print(f"  RESTRICCIÓN UNIQUE: {unique}")

            for check in inspector.get_check_constraints(
                table_name, schema=schema
            ):
                print(f"  RESTRICCIÓN CHECK: {check}")

            for index in inspector.get_indexes(
                table_name, schema=schema
            ):
                print(f"  ÍNDICE: {index}")

            print()

        if views:
            print("VISTAS:")
            for view_name in views:
                print(f"  - {view_name}")

    print("Inspección terminada. No se modificó el esquema.")


if __name__ == "__main__":
    main()