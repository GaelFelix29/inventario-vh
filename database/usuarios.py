from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from database.conexion import engine


# ==========================================
# CREAR USUARIO
# ==========================================

def crear_usuario(nombre, usuario, correo, password, rol="Visualizador"):

    password_hash = generate_password_hash(password)

    sql = text("""
        INSERT INTO usuarios
        (
            nombre,
            usuario,
            correo,
            password,
            rol,
            activo
        )
        VALUES
        (
            :nombre,
            :usuario,
            :correo,
            :password,
            :rol,
            1
        )
    """)

    with engine.begin() as conn:
        conn.execute(sql, {
            "nombre": nombre,
            "usuario": usuario,
            "correo": correo,
            "password": password_hash,
            "rol": rol
        })


# ==========================================
# OBTENER USUARIO LOGIN
# ==========================================

def obtener_usuario(usuario):

    sql = text("""
        SELECT *
        FROM usuarios
        WHERE usuario = :usuario
        AND activo = 1
    """)

    with engine.connect() as conn:
        resultado = conn.execute(sql, {
            "usuario": usuario
        })

        return resultado.fetchone()
    
# ==========================================
# OBTENER USUARIO POR ID
# ==========================================

def obtener_usuario_id(id):

    sql = text("""
        SELECT *
        FROM usuarios
        WHERE id = :id
    """)

    with engine.connect() as conn:

        resultado = conn.execute(sql, {
            "id": id
        })

        return resultado.mappings().first()
    
# ==========================================
# ACTUALIZAR USUARIO
# ==========================================

def actualizar_usuario(id,
                        nombre,
                        usuario,
                        correo,
                        rol,
                        activo):

    sql = text("""
        UPDATE usuarios
        SET
            nombre = :nombre,
            usuario = :usuario,
            correo = :correo,
            rol = :rol,
            activo = :activo
        WHERE id = :id
    """)

    with engine.begin() as conn:

        conn.execute(sql, {

            "id": id,
            "nombre": nombre,
            "usuario": usuario,
            "correo": correo,
            "rol": rol,
            "activo": activo

        })


# ==========================================
# LISTAR USUARIOS
# ==========================================

def obtener_usuarios():

    sql = text("""
        SELECT *
        FROM usuarios
        ORDER BY nombre
    """)

    with engine.connect() as conn:
        resultado = conn.execute(sql)

        return resultado.mappings().all()
    
# ==========================================
# DESACTIVAR USUARIO
# ==========================================

def desactivar_usuario(id):

    sql = text("""
        UPDATE usuarios
        SET activo = 0
        WHERE id = :id
    """)

    with engine.begin() as conn:

        conn.execute(sql, {
            "id": id
        })


# ==========================================
# REACTIVAR USUARIO
# ==========================================

def reactivar_usuario(id):

    sql = text("""
        UPDATE usuarios
        SET activo = 1
        WHERE id = :id
    """)

    with engine.begin() as conn:

        conn.execute(sql, {
            "id": id
        })

# ==========================================
# ACTUALIZAR CONTRASEÑA
# ==========================================

def actualizar_password(id, password):
    password_hash = generate_password_hash(password)

    sql = text("""
        UPDATE usuarios
        SET password = :password,
            debe_cambiar_password = 0
        WHERE id = :id
        AND activo = 1
    """)

    with engine.begin() as conn:
        resultado = conn.execute(sql, {
            "id": id,
            "password": password_hash
        })

        if resultado.rowcount != 1:
            raise ValueError(
                "No fue posible actualizar la contraseña."
            )


def establecer_password_temporal(id, password_temporal):
    password_hash = generate_password_hash(password_temporal)

    sql = text("""
        UPDATE usuarios
        SET password = :password,
            debe_cambiar_password = 1
        WHERE id = :id
        AND activo = 1
    """)

    with engine.begin() as conn:
        resultado = conn.execute(sql, {
            "id": id,
            "password": password_hash
        })

        if resultado.rowcount != 1:
            raise ValueError(
                "No fue posible restablecer la contraseña."
            )


# ==========================================
# VERIFICAR PASSWORD
# ==========================================

def verificar_password(password, password_hash):

    return check_password_hash(password_hash, password)

# ==========================================
# ACTUALIZAR PERFIL PROPIO
# ==========================================

AVATARES_PERMITIDOS = {
    "usuario",
    "finanzas",
    "mantenimiento",
    "administracion",
    "seguridad",
    "inventario",
    "logistica",
    "ejecutivo"
}


def actualizar_perfil(
    id_usuario,
    nombre,
    avatar
):

    if avatar not in AVATARES_PERMITIDOS:

        raise ValueError(
            "El avatar seleccionado no es válido."
        )

    sql = text("""
        UPDATE usuarios
        SET
            nombre = :nombre,
            avatar = :avatar
        WHERE id = :id_usuario
        AND activo = 1
    """)

    with engine.begin() as conn:

        resultado = conn.execute(
            sql,
            {
                "id_usuario": id_usuario,
                "nombre": nombre,
                "avatar": avatar
            }
        )

        if resultado.rowcount != 1:

            raise ValueError(
                "No fue posible actualizar el perfil."
            )