#!/usr/bin/env python3
#
# smart_backup.py - Respaldo Modular v4.1 (FULL BACKUP INTEGRADO + VALIDACIÓN)
# Autor: Alex Callejas

# smart_backup.py - Smart Backup v5.0
# Respaldo modular para Linux

import datetime
import os
import shutil
import subprocess
import sys
import tempfile


# ============================================================
# CONFIGURACIÓN
# ============================================================

VERSION = "5.0"

SIZE_THRESHOLD = 5 * 1024 * 1024 * 1024
SUB_SIZE_THRESHOLD = 500 * 1024 * 1024

HOME = os.path.expanduser("~")
USER = os.environ.get("USER", os.path.basename(HOME) or "usuario")

SUPPORTED_COMPAT_FILESYSTEMS = {
    "exfat",
    "vfat",
    "fuseblk",
    "ntfs",
}

SYSTEM_ITEMS = [
    ".bashrc",
    ".bash_profile",
    ".bash_history",
    ".zshrc",
    ".ssh",
    "bin",
    ".gitconfig",
    ".git-credentials",
    ".vim",
    ".vimrc",
    ".viminfo",
    ".ansible",
    ".aws",
    ".ollama",
    ".claude",
    ".claude.json",
    ".gemini",
    ".continue",
    ".vale-styles",
    ".vale.ini",
    ".config",
    ".local",
]


# ============================================================
# COLORES
# ============================================================

class Colors:
    RESET = "\033[0m"

    BOLD = "\033[1m"
    DIM = "\033[2m"

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BG_BLUE = "\033[44m"
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"


def supports_color():
    """
    Determina si la terminal soporta colores ANSI.
    """
    return sys.stdout.isatty() and os.environ.get("TERM") != "dumb"


COLOR_ENABLED = supports_color()


def color(text, color_code):
    """
    Aplica color únicamente si la terminal lo soporta.
    """
    if not COLOR_ENABLED:
        return text

    return f"{color_code}{text}{Colors.RESET}"


# ============================================================
# INTERFAZ
# ============================================================

def clear_screen():
    """
    Limpia la pantalla.
    """
    if not sys.stdout.isatty():
        return

    os.system("clear")


def pause(message="Presiona Enter para continuar..."):
    """
    Pausa la ejecución.
    """
    try:
        input(f"\n{color(message, Colors.DIM)}")
    except (KeyboardInterrupt, EOFError):
        print()
        return


def show_header(title, subtitle=None):
    """
    Muestra un encabezado uniforme.
    """
    width = 62

    print()
    print(color("=" * width, Colors.BLUE))
    print(color(f" {title}", Colors.BOLD + Colors.CYAN))

    if subtitle:
        print(color(f" {subtitle}", Colors.DIM))

    print(color("=" * width, Colors.BLUE))
    print()


def show_section(title):
    """
    Muestra un separador de sección.
    """
    print()
    print(color(f"--- {title} ---", Colors.BOLD + Colors.CYAN))


def info(message):
    print(f"{color('[INFO]', Colors.CYAN)}  {message}")


def success(message):
    print(f"{color('[ OK ]', Colors.GREEN)}  {message}")


def warning(message):
    print(f"{color('[WARN]', Colors.YELLOW)}  {message}")


def error(message):
    print(f"{color('[ERROR]', Colors.RED)} {message}")


def prompt(message):
    """
    Input estándar con formato uniforme.
    """
    try:
        return input(f"\n{color('>', Colors.CYAN)} {message} ").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        return ""


def ask_yes_no(message, default=False):
    """
    Pregunta de tipo sí/no.

    Enter utiliza el valor default.
    """
    default_text = "S/n" if default else "s/N"

    while True:
        answer = prompt(f"{message} [{default_text}]").lower()

        if not answer:
            return default

        if answer in ("s", "si", "sí", "y", "yes"):
            return True

        if answer in ("n", "no"):
            return False

        warning("Respuesta no válida. Utiliza 's' o 'n'.")


def ask_option(message, valid_options):
    """
    Solicita una opción perteneciente a una lista.
    """
    valid_options = [str(option).lower() for option in valid_options]

    while True:
        answer = prompt(message).lower()

        if answer in valid_options:
            return answer

        warning(
            f"Opción no válida. Opciones disponibles: "
            f"{', '.join(valid_options)}"
        )


# ============================================================
# UTILIDADES
# ============================================================

def format_size(size_in_bytes):
    """
    Convierte bytes a una unidad legible.
    """
    size = float(size_in_bytes)

    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if size < 1024:
            return f"{size:.1f} {unit}"

        size /= 1024

    return f"{size:.1f} EB"


def format_number(number):
    """
    Formatea números con separadores.
    """
    return f"{number:,}"


def get_size(path):
    """
    Calcula el tamaño de un archivo o directorio.

    Los enlaces simbólicos no se siguen.
    """
    try:
        if os.path.islink(path):
            return 0

        if os.path.isfile(path):
            return os.path.getsize(path)

        if not os.path.isdir(path):
            return 0

    except OSError:
        return 0

    total_size = 0

    try:
        for dirpath, dirnames, filenames in os.walk(
            path,
            topdown=True,
            followlinks=False,
        ):
            # Evitar seguir symlinks a directorios.
            dirnames[:] = [
                dirname
                for dirname in dirnames
                if not os.path.islink(os.path.join(dirpath, dirname))
            ]

            for filename in filenames:
                filepath = os.path.join(dirpath, filename)

                try:
                    if os.path.islink(filepath):
                        continue

                    total_size += os.path.getsize(filepath)

                except (OSError, PermissionError):
                    continue

    except (OSError, PermissionError):
        pass

    return total_size


def path_exists(path):
    """
    Comprueba si existe un archivo o directorio.
    """
    try:
        return os.path.exists(path)
    except OSError:
        return False


def safe_remove(path):
    """
    Elimina un archivo si existe.
    """
    try:
        if os.path.exists(path):
            os.remove(path)

    except OSError as exc:
        warning(f"No se pudo eliminar el archivo temporal: {exc}")


# ============================================================
# INFORMACIÓN DEL DISCO
# ============================================================

def get_filesystem_type(path):
    """
    Obtiene el tipo de filesystem utilizando df.

    Devuelve 'unknown' si no puede determinarse.
    """
    try:
        result = subprocess.run(
            ["df", "-T", path],
            capture_output=True,
            text=True,
            check=True,
        )

        lines = result.stdout.strip().splitlines()

        if len(lines) < 2:
            return "unknown"

        fields = lines[-1].split()

        if len(fields) >= 2:
            return fields[1].lower()

    except (subprocess.SubprocessError, OSError):
        pass

    return "unknown"


def get_disk_usage(path):
    """
    Obtiene información del disco donde se encuentra path.
    """
    try:
        return shutil.disk_usage(path)

    except OSError:
        return None


def show_disk_info(dest_path):
    """
    Muestra información del disco destino.
    """
    clear_screen()

    show_header(
        "INFORMACIÓN DEL DISCO",
        "Estado actual del destino seleccionado",
    )

    filesystem = get_filesystem_type(dest_path)
    usage = get_disk_usage(dest_path)

    print(f"  Ruta         : {dest_path}")
    print(f"  Filesystem   : {filesystem}")

    if usage:
        total = usage.total
        used = total - usage.free

        print(f"  Capacidad    : {format_size(total)}")
        print(f"  Utilizado    : {format_size(used)}")
        print(f"  Disponible   : {format_size(usage.free)}")

        if total > 0:
            percentage = (used / total) * 100
            print(f"  Uso          : {percentage:.1f}%")

    else:
        warning("No se pudo obtener información del disco.")

    pause()


# ============================================================
# ANÁLISIS DE DIRECTORIOS
# ============================================================

def get_heavy_items(directory, threshold):
    """
    Obtiene elementos cuyo tamaño sea igual o superior
    al threshold indicado.
    """
    items = []

    if not os.path.isdir(directory):
        return items

    try:
        entries = os.scandir(directory)

        with entries as iterator:
            for entry in iterator:
                if entry.name.startswith("."):
                    continue

                try:
                    size = get_size(entry.path)

                    if size >= threshold:
                        items.append((entry.path, size))

                except (OSError, PermissionError):
                    continue

    except (OSError, PermissionError):
        pass

    return sorted(
        items,
        key=lambda item: item[1],
        reverse=True,
    )


def show_heavy_items(items):
    """
    Muestra una lista de elementos pesados.
    """
    if not items:
        return

    print()

    for path, size in items:
        name = os.path.basename(path) or path

        print(
            f"  {color(format_size(size), Colors.YELLOW):>18}  "
            f"{name}"
        )


# ============================================================
# ARCHIVOS DE ARCHIVO
# ============================================================

def get_archive_dir(base_dest, prefix):
    """
    Genera un directorio de backup único.

    Ejemplo:
        FullBackup_17Sep2026
        FullBackup_17Sep2026_1
    """
    months = {
        1: "Ene",
        2: "Feb",
        3: "Mar",
        4: "Abr",
        5: "May",
        6: "Jun",
        7: "Jul",
        8: "Ago",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dic",
    }

    now = datetime.datetime.now()

    date_str = (
        f"{now.day}"
        f"{months[now.month]}"
        f"{now.year}"
    )

    base_name = f"{prefix}_{date_str}"

    target_dir = os.path.join(
        base_dest,
        base_name,
    )

    if not os.path.exists(target_dir):
        return target_dir

    counter = 1

    while True:
        target_dir = os.path.join(
            base_dest,
            f"{base_name}_{counter}",
        )

        if not os.path.exists(target_dir):
            return target_dir

        counter += 1


# ============================================================
# RESPALDO DEL SISTEMA
# ============================================================

def get_system_items():
    """
    Obtiene los elementos del HOME que existen actualmente.
    """
    return [
        item
        for item in SYSTEM_ITEMS
        if path_exists(os.path.join(HOME, item))
    ]


def show_system_items(items, sizes):
    """
    Muestra los elementos seleccionados para el backup.
    """
    print()

    sorted_items = sorted(
        items,
        key=lambda item: sizes.get(item, 0),
        reverse=True,
    )

    for item in sorted_items:
        size = sizes.get(item, 0)

        print(
            f"  {format_size(size):>12}  "
            f"{item}"
        )


def backup_system(dest_path):
    """
    Ejecuta el respaldo de configuración del sistema.
    """
    clear_screen()

    show_header(
        "RESPALDO DEL SISTEMA",
        "Dotfiles y configuraciones seleccionadas",
    )

    try:
        os.makedirs(dest_path, exist_ok=True)

    except OSError as exc:
        error(f"No se pudo crear el destino: {exc}")
        pause()
        return False

    tar_filename = (
        f"perfil_{USER}_"
        f"{datetime.datetime.now().strftime('%Y-%m-%d')}.tar.gz"
    )

    tar_filepath = os.path.join(
        dest_path,
        tar_filename,
    )

    to_pack = get_system_items()

    if not to_pack:
        error("No se encontraron elementos para respaldar.")
        pause()
        return False

    info("Calculando tamaños de los elementos...")

    item_sizes = {}

    for item in to_pack:
        item_path = os.path.join(HOME, item)
        item_sizes[item] = get_size(item_path)

    show_section("Elementos seleccionados")

    show_system_items(to_pack, item_sizes)

    # --------------------------------------------------------
    # EXCLUSIÓN DE ELEMENTOS
    # --------------------------------------------------------

    while True:
        if not ask_yes_no(
            "¿Quieres excluir algún elemento?",
            default=False,
        ):
            break

        item_to_remove = prompt(
            "Nombre del elemento a excluir"
        )

        if item_to_remove in to_pack:
            to_pack.remove(item_to_remove)

            success(
                f"Excluido: {item_to_remove}"
            )

        else:
            warning(
                "Ese elemento no se encuentra "
                "en la selección actual."
            )

        if not to_pack:
            error(
                "No quedan elementos seleccionados."
            )
            pause()
            return False

    # --------------------------------------------------------
    # AGREGAR ELEMENTOS
    # --------------------------------------------------------

    while True:
        if not ask_yes_no(
            "¿Quieres agregar otro archivo o directorio?",
            default=False,
        ):
            break

        extra_item = prompt(
            "Nombre relativo a HOME"
        )

        extra_path = os.path.join(
            HOME,
            extra_item,
        )

        if not path_exists(extra_path):
            warning(
                "El elemento no existe dentro de tu HOME."
            )
            continue

        if extra_item in to_pack:
            warning(
                "Ese elemento ya está seleccionado."
            )
            continue

        to_pack.append(extra_item)

        item_sizes[extra_item] = get_size(
            extra_path
        )

        success(
            f"Agregado: {extra_item} "
            f"({format_size(item_sizes[extra_item])})"
        )

    if not to_pack:
        error(
            "No se seleccionó ningún elemento."
        )
        pause()
        return False

    # --------------------------------------------------------
    # RESUMEN
    # --------------------------------------------------------

    total_sys_size = sum(
        item_sizes.get(item, 0)
        for item in to_pack
    )

    destination_parent = os.path.dirname(
        os.path.abspath(dest_path)
    )

    usage = get_disk_usage(
        destination_parent
    )

    if usage is None:
        error(
            "No se pudo determinar el espacio disponible."
        )
        pause()
        return False

    free_space = usage.free

    show_section("Resumen")

    print(
        f"  Elementos       : {len(to_pack)}"
    )

    print(
        f"  Tamaño estimado : "
        f"{format_size(total_sys_size)}"
    )

    print(
        f"  Espacio libre   : "
        f"{format_size(free_space)}"
    )

    if total_sys_size > free_space:
        error(
            "No hay suficiente espacio disponible "
            "en el destino."
        )

        pause()
        return False

    print()
    warning(
        "El backup será creado como archivo .tar.gz."
    )

    if not ask_yes_no(
        "¿Proceder con la creación del backup?",
        default=False,
    ):
        info("Operación cancelada.")
        pause()
        return False

    # --------------------------------------------------------
    # TAR
    # --------------------------------------------------------

    show_section("Creando backup")

    info(
        "Ejecutando tar. "
        "El proceso puede tardar dependiendo del tamaño."
    )

    cmd = [
        "tar",
        "-czf",
        tar_filepath,
    ] + to_pack

    try:
        result = subprocess.run(
            cmd,
            cwd=HOME,
        )

    except OSError as exc:
        error(
            f"No se pudo ejecutar tar: {exc}"
        )
        pause()
        return False

    if result.returncode != 0:
        error(
            f"tar terminó con código "
            f"{result.returncode}."
        )

        if os.path.exists(tar_filepath):
            warning(
                "Se eliminará el archivo incompleto."
            )
            safe_remove(tar_filepath)

        pause()
        return False

    if not os.path.exists(tar_filepath):
        error(
            "tar terminó correctamente, "
            "pero el archivo no fue encontrado."
        )
        pause()
        return False

    archive_size = os.path.getsize(
        tar_filepath
    )

    success("Respaldo del sistema completado.")

    print()
    print(
        f"  Archivo : {tar_filename}"
    )
    print(
        f"  Tamaño  : {format_size(archive_size)}"
    )
    print(
        f"  Ruta    : {dest_path}"
    )

    pause()

    return True


# ============================================================
# RESPALDO PERSONAL
# ============================================================

def analyze_home():
    """
    Analiza los elementos pesados del HOME.
    """
    clear_screen()

    show_header(
        "ANÁLISIS PERSONAL",
        f"Buscando elementos mayores a "
        f"{format_size(SIZE_THRESHOLD)}",
    )

    info(
        f"Analizando: {HOME}"
    )

    info(
        "Este proceso puede tardar dependiendo "
        "del tamaño del HOME."
    )

    heavy_items = get_heavy_items(
        HOME,
        SIZE_THRESHOLD,
    )

    if not heavy_items:
        warning(
            "No se encontraron elementos pesados."
        )
        pause()
        return []

    show_section(
        "Elementos encontrados"
    )

    show_heavy_items(heavy_items)

    return heavy_items


def select_personal_items(heavy_items):
    """
    Permite decidir qué hacer con cada elemento pesado.
    """
    to_sync = []

    for path, size in heavy_items:
        name = os.path.basename(path)

        show_section(
            f"{name} - {format_size(size)}"
        )

        if os.path.isdir(path):
            print(
                "  [R] Respaldar directorio completo"
            )
            print(
                "  [D] Depurar internamente"
            )
            print(
                "  [I] Ignorar"
            )

            action = ask_option(
                "Selecciona una opción [R/D/I]",
                ["r", "d", "i"],
            )

            if action == "r":
                to_sync.append(path)

            elif action == "d":
                sub_items = get_heavy_items(
                    path,
                    SUB_SIZE_THRESHOLD,
                )

                if not sub_items:
                    warning(
                        "No se encontraron elementos "
                        f"mayores a "
                        f"{format_size(SUB_SIZE_THRESHOLD)}."
                    )
                    continue

                print()
                print(
                    f"Contenido pesado de {name}:"
                )

                for sub_path, sub_size in sub_items:
                    sub_name = os.path.basename(
                        sub_path
                    )

                    print()
                    print(
                        f"  {format_size(sub_size):>12}  "
                        f"{sub_name}"
                    )

                    sub_action = ask_option(
                        "  ¿[R] Respaldar o [I] Ignorar?",
                        ["r", "i"],
                    )

                    if sub_action == "r":
                        to_sync.append(sub_path)

        else:
            print(
                "  [R] Respaldar"
            )
            print(
                "  [I] Ignorar"
            )

            action = ask_option(
                "Selecciona una opción [R/I]",
                ["r", "i"],
            )

            if action == "r":
                to_sync.append(path)

    return to_sync


def add_personal_items(to_sync):
    """
    Permite agregar archivos/directorios manualmente.
    """
    while True:
        if not ask_yes_no(
            "¿Quieres agregar otro archivo o directorio?",
            default=False,
        ):
            break

        extra_path = prompt(
            "Ruta relativa a HOME"
        )

        if not extra_path:
            warning("La ruta no puede estar vacía.")
            continue

        full_path = os.path.abspath(
            os.path.join(
                HOME,
                extra_path,
            )
        )

        # Evitar que el usuario salga de HOME.
        home_real = os.path.realpath(HOME)
        full_real = os.path.realpath(full_path)

        try:
            inside_home = os.path.commonpath(
                [home_real, full_real]
            ) == home_real

        except ValueError:
            inside_home = False

        if not inside_home:
            error(
                "La ruta debe encontrarse dentro "
                "de tu HOME."
            )
            continue

        if not path_exists(full_path):
            warning(
                "El path no existe."
            )
            continue

        if full_path in to_sync:
            warning(
                "Ese elemento ya está seleccionado."
            )
            continue

        to_sync.append(full_path)

        success(
            f"Agregado: "
            f"{os.path.relpath(full_path, HOME)}"
        )

    return to_sync


def create_rsync_file_list(to_sync):
    """
    Crea un archivo temporal para --files-from.
    """
    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        prefix="smart_backup_",
        suffix=".list",
        delete=False,
        encoding="utf-8",
    )

    try:
        for item in to_sync:
            relative_path = os.path.relpath(
                item,
                HOME,
            )

            temp_file.write(
                f"{relative_path}\n"
            )

        temp_file.close()

        return temp_file.name

    except Exception:
        temp_file.close()
        safe_remove(temp_file.name)
        raise


def cleanup_empty_directories(items):
    """
    Elimina directorios vacíos que hayan quedado
    después del movimiento.
    """
    info(
        "Limpiando directorios vacíos remanentes..."
    )

    for item in items:
        if not os.path.isdir(item):
            continue

        try:
            subprocess.run(
                [
                    "find",
                    item,
                    "-mindepth",
                    "1",
                    "-type",
                    "d",
                    "-empty",
                    "-delete",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )

        except OSError:
            continue


def backup_personal(dest_path, rsync_flags):
    """
    Ejecuta el respaldo personal mediante rsync.
    """
    clear_screen()

    show_header(
        "RESPALDO PERSONAL",
        "Selección y movimiento de archivos",
    )

    heavy_items = analyze_home()

    if not heavy_items:
        return False

    to_sync = select_personal_items(
        heavy_items
    )

    to_sync = add_personal_items(
        to_sync
    )

    if not to_sync:
        warning(
            "No seleccionaste ningún elemento."
        )
        pause()
        return False

    # --------------------------------------------------------
    # ELIMINAR DUPLICADOS / RUTAS CONTENIDAS
    # --------------------------------------------------------

    normalized_items = []

    for item in to_sync:
        item = os.path.abspath(item)

        if item not in normalized_items:
            normalized_items.append(item)

    to_sync = normalized_items

    # --------------------------------------------------------
    # RESUMEN
    # --------------------------------------------------------

    clear_screen()

    show_header(
        "CONFIRMACIÓN DEL RESPALDO PERSONAL"
    )

    total_bytes = 0

    print(
        "Elementos que serán movidos:"
    )

    for item in to_sync:
        size = get_size(item)
        total_bytes += size

        relative = os.path.relpath(
            item,
            HOME,
        )

        print(
            f"  {format_size(size):>12}  "
            f"{relative}"
        )

    destination_parent = os.path.dirname(
        os.path.abspath(dest_path)
    )

    usage = get_disk_usage(
        destination_parent
    )

    if usage is None:
        error(
            "No se pudo determinar el espacio "
            "disponible en el destino."
        )
        pause()
        return False

    free_space = usage.free

    show_section("Espacio")

    print(
        f"  Tamaño seleccionado : "
        f"{format_size(total_bytes)}"
    )

    print(
        f"  Espacio disponible  : "
        f"{format_size(free_space)}"
    )

    if total_bytes > free_space:
        error(
            "No hay suficiente espacio disponible "
            "en el destino."
        )
        pause()
        return False

    print()

    warning(
        "Esta operación moverá los archivos "
        "y eliminará los archivos originales "
        "después de una transferencia exitosa."
    )

    if not ask_yes_no(
        "¿Deseas continuar?",
        default=False,
    ):
        info("Operación cancelada.")
        pause()
        return False

    # --------------------------------------------------------
    # PREPARAR DESTINO
    # --------------------------------------------------------

    try:
        os.makedirs(
            dest_path,
            exist_ok=True,
        )

    except OSError as exc:
        error(
            f"No se pudo crear el destino: {exc}"
        )
        pause()
        return False

    log_file_path = os.path.join(
        dest_path,
        "backup_registro.log",
    )

    list_file = None

    try:
        list_file = create_rsync_file_list(
            to_sync
        )

        # ----------------------------------------------------
        # RSYNC
        # ----------------------------------------------------

        clear_screen()

        show_header(
            "RESPALDO PERSONAL",
            "Transferencia mediante rsync",
        )

        info(
            "Iniciando transferencia..."
        )

        info(
            f"Registro: {log_file_path}"
        )

        cmd = [
            "rsync",
            rsync_flags,
            f"--log-file={log_file_path}",
            f"--files-from={list_file}",
            "--remove-source-files",
            f"{HOME}/",
            f"{dest_path}/",
        ]

        result = subprocess.run(
            cmd,
            check=False,
        )

        if result.returncode != 0:
            error(
                "rsync terminó con errores."
            )

            error(
                f"Código de salida: "
                f"{result.returncode}"
            )

            print()
            print(
                f"Revisa el log en:"
            )
            print(
                f"  {log_file_path}"
            )

            pause()
            return False

        success(
            "Transferencia completada."
        )

        cleanup_empty_directories(
            to_sync
        )

        print()
        success(
            "Respaldo personal completado."
        )

        print(
            f"  Espacio procesado: "
            f"{format_size(total_bytes)}"
        )

        print(
            f"  Destino          : "
            f"{dest_path}"
        )

        print(
            f"  Log              : "
            f"{log_file_path}"
        )

        pause()

        return True

    except OSError as exc:
        error(
            f"Error durante la operación: {exc}"
        )

        pause()
        return False

    finally:
        if list_file:
            safe_remove(list_file)


# ============================================================
# CONFIGURACIÓN DE RSYNC
# ============================================================

def get_rsync_flags(filesystem):
    """
    Determina las banderas apropiadas para rsync.
    """
    if filesystem in SUPPORTED_COMPAT_FILESYSTEMS:
        return "-rtvh"

    return "-avh"


def show_destination_status(dest_path):
    """
    Muestra el estado del destino antes del menú principal.
    """
    filesystem = get_filesystem_type(
        dest_path
    )

    usage = get_disk_usage(
        dest_path
    )

    print(
        f"  Destino     : {dest_path}"
    )

    print(
        f"  Filesystem  : {filesystem}"
    )

    if usage:
        print(
            f"  Disponible  : "
            f"{format_size(usage.free)}"
        )

        print(
            f"  Capacidad   : "
            f"{format_size(usage.total)}"
        )

    return filesystem


# ============================================================
# MENÚ PRINCIPAL
# ============================================================

def show_main_menu(dest_path):
    """
    Muestra el menú principal.
    """
    clear_screen()

    show_header(
        f"SMART BACKUP v{VERSION}",
        "Respaldo modular para Linux",
    )

    show_section("Destino")

    filesystem = show_destination_status(
        dest_path
    )

    rsync_flags = get_rsync_flags(
        filesystem
    )

    print()
    print(
        color(
            "  MENU PRINCIPAL",
            Colors.BOLD,
        )
    )

    print()
    print(
        "  [1] Respaldo personal"
    )

    print(
        "  [2] Respaldo del sistema"
    )

    print(
        "  [3] Respaldo completo"
    )

    print(
        "  [4] Información del disco"
    )

    print(
        "  [5] Salir"
    )

    print()

    return filesystem, rsync_flags


# ============================================================
# RESPALDO COMPLETO
# ============================================================

def backup_full(dest_path, rsync_flags):
    """
    Ejecuta primero el respaldo personal y luego
    el respaldo del sistema.
    """
    clear_screen()

    show_header(
        "RESPALDO COMPLETO",
        "Personal + Sistema",
    )

    full_backup_dir = get_archive_dir(
        dest_path,
        "FullBackup",
    )

    personal_dir = os.path.join(
        full_backup_dir,
        "PersonalArchive",
    )

    system_dir = os.path.join(
        full_backup_dir,
        "SystemBackup",
    )

    try:
        os.makedirs(
            full_backup_dir,
            exist_ok=True,
        )

    except OSError as exc:
        error(
            f"No se pudo crear el directorio "
            f"del backup: {exc}"
        )
        pause()
        return False

    print(
        f"Directorio del respaldo:"
    )
    print(
        f"  {full_backup_dir}"
    )

    print()
    warning(
        "El respaldo completo ejecutará dos etapas:"
    )

    print(
        "  1. Respaldo personal"
    )

    print(
        "  2. Respaldo del sistema"
    )

    if not ask_yes_no(
        "¿Deseas iniciar el respaldo completo?",
        default=False,
    ):
        info("Operación cancelada.")
        pause()
        return False

    # --------------------------------------------------------
    # PERSONAL
    # --------------------------------------------------------

    personal_result = backup_personal(
        personal_dir,
        rsync_flags,
    )

    if not personal_result:
        warning(
            "El respaldo personal no se completó."
        )

        if not ask_yes_no(
            "¿Deseas continuar con el respaldo del sistema?",
            default=False,
        ):
            return False

    # --------------------------------------------------------
    # SISTEMA
    # --------------------------------------------------------

    system_result = backup_system(
        system_dir
    )

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    clear_screen()

    show_header(
        "RESUMEN DEL RESPALDO COMPLETO"
    )

    print(
        f"  Directorio:"
    )

    print(
        f"  {full_backup_dir}"
    )

    print()

    if personal_result:
        success(
            "Respaldo personal completado."
        )
    else:
        warning(
            "Respaldo personal no completado."
        )

    if system_result:
        success(
            "Respaldo del sistema completado."
        )
    else:
        warning(
            "Respaldo del sistema no completado."
        )

    print()

    if personal_result and system_result:
        success(
            "Todas las etapas finalizaron correctamente."
        )
        result = True

    else:
        warning(
            "El respaldo completo terminó "
            "con una o más etapas pendientes."
        )
        result = False

    pause()

    return result


# ============================================================
# VALIDACIÓN DEL DESTINO
# ============================================================

def validate_destination(dest_path):
    """
    Comprueba que el destino sea un directorio válido.
    """
    if not dest_path:
        return False

    if not os.path.exists(dest_path):
        error(
            f"La ruta no existe: {dest_path}"
        )
        return False

    if not os.path.isdir(dest_path):
        error(
            f"La ruta no es un directorio: {dest_path}"
        )
        return False

    if not os.access(dest_path, os.W_OK):
        error(
            "No tienes permisos de escritura "
            "en el destino."
        )
        return False

    return True


def request_destination():
    """
    Solicita la ruta del disco externo.
    """
    clear_screen()

    show_header(
        f"SMART BACKUP v{VERSION}",
        "Configuración inicial",
    )

    print(
        "Introduce la ruta donde se almacenarán "
        "los respaldos."
    )

    print()
    print(
        "Ejemplo:"
    )

    print(
        "  /run/media/TU_USUARIO/TU_DISCO"
    )

    while True:
        dest_path = prompt(
            "Ruta del disco externo"
        )

        if validate_destination(
            dest_path
        ):
            return os.path.abspath(
                dest_path
            )

        print()

        if not ask_yes_no(
            "¿Quieres introducir otra ruta?",
            default=True,
        ):
            return None


# ============================================================
# MAIN
# ============================================================

def main():
    """
    Punto de entrada principal.
    """
    try:
        dest_dir = request_destination()

        if not dest_dir:
            print()
            info("Programa finalizado.")
            return 0

        filesystem = get_filesystem_type(
            dest_dir
        )

        rsync_flags = get_rsync_flags(
            filesystem
        )

        if filesystem in SUPPORTED_COMPAT_FILESYSTEMS:
            warning(
                f"Filesystem '{filesystem}' detectado."
            )

            info(
                "Se utilizarán banderas de "
                "compatibilidad para rsync."
            )

            info(
                f"Rsync: {rsync_flags}"
            )

        else:
            info(
                f"Filesystem '{filesystem}' detectado."
            )

            info(
                f"Rsync: {rsync_flags}"
            )

        pause(
            "Presiona Enter para abrir el menú principal..."
        )

        while True:
            filesystem, rsync_flags = show_main_menu(
                dest_dir
            )

            option = prompt(
                "Selecciona una opción"
            ).lower()

            if option == "1":
                backup_personal(
                    get_archive_dir(
                        dest_dir,
                        "PersonalArchive",
                    ),
                    rsync_flags,
                )

            elif option == "2":
                backup_system(
                    get_archive_dir(
                        dest_dir,
                        "SystemBackup",
                    )
                )

            elif option == "3":
                backup_full(
                    dest_dir,
                    rsync_flags,
                )

            elif option == "4":
                show_disk_info(
                    dest_dir
                )

            elif option == "5":
                clear_screen()

                show_header(
                    f"SMART BACKUP v{VERSION}"
                )

                success(
                    "Programa finalizado."
                )

                print()

                return 0

            else:
                warning(
                    "Opción no válida."
                )
                pause()

    except KeyboardInterrupt:
        print()
        print()
        warning(
            "Operación interrumpida por el usuario."
        )
        print()
        return 130

    except Exception as exc:
        print()
        error(
            f"Error inesperado: {exc}"
        )
        print()
        return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    sys.exit(main())