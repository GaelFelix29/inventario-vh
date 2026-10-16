"""Genera el valor seguro para RESPALDOS_PASSWORD_HASH sin guardar la contraseña."""

from getpass import getpass

from werkzeug.security import generate_password_hash


def main():
    clave = getpass("Nueva contraseña exclusiva de Respaldos: ")
    confirmacion = getpass("Confirma la contraseña: ")
    if clave != confirmacion:
        raise SystemExit("Las contraseñas no coinciden.")
    if len(clave) < 12:
        raise SystemExit("Usa una contraseña de al menos 12 caracteres.")
    print("\nCopia este valor en RESPALDOS_PASSWORD_HASH:\n")
    print(generate_password_hash(clave))


if __name__ == "__main__":
    main()
