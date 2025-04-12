#!/usr/bin/env python3
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Configuration
MAX_LINE_COUNT = 1500  # Máximo número de líneas por archivo
MAX_FILE_SIZE_MB = 10  # Máximo tamaño de archivo en MB para procesar
MAX_OUTPUT_SIZE_MB = 100  # Límite de tamaño máximo para el archivo de salida en MB
IGNORED_EXTENSIONS = ['.lock', '.pyc', '.pyo', '.pyd', '.class', '.jar', '.war', '.ear', '.dll', '.exe', '.so', '.o',
                     '.bin', '.obj', '.dat', '.db', '.sqlite', '.bak', '.tmp', '.temp', '.log', '.pdf', '.zip', '.gz',
                     '.tar', '.7z', '.rar', '.iso', '.min.js', '.min.css', '.map', '.bundle.js', '.d.ts']
IGNORED_DIRS = ['.venv', 'venv', 'node_modules', '.git', '__pycache__', 'target', 'build', 'dist', '.idea', '.vs', '.vscode',
               'bin', 'obj', 'out', 'Debug', 'Release', 'logs', 'temp', '.mvn', '.gradle', 'gradle', 'gradle-wrapper',
               '.settings', '.metadata', 'META-INF', 'WEB-INF', 'gen', 'generated', 'generated-sources', 'classes',
               'node', 'bower_components', 'coverage', 'report', 'reports', 'deps', 'vendor', 'jspm_packages',
               'compiled', 'resources', 'assets', 'static', 'libs', 'lib', 'Library', 'Frameworks']
IGNORED_FILES = ['package-lock.json', 'yarn.lock', 'Pipfile.lock', 'poetry.lock', '.gitignore', '.gitattributes',
                '.classpath', '.project', 'gradlew', 'gradlew.bat', 'mvnw', 'mvnw.cmd', 'Thumbs.db', '.DS_Store',
                'pom.xml.versionsBackup', 'application.properties', 'application.yml', 'application-dev.properties',
                'application-prod.properties', 'bootstrap.properties', 'bootstrap.yml','code_structure_generator.py']

def count_lines(file_path):
    """Count the number of lines in a file."""
    try:
        with open(file_path, 'rb') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

def get_file_size_mb(file_path):
    """Get file size in MB."""
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except Exception:
        return 0

def is_binary_file(file_path):
    """Check if a file is binary."""
    try:
        # Primero comprobamos por extensión
        ext = os.path.splitext(file_path)[1].lower()
        if ext in IGNORED_EXTENSIONS:
            return True

        # Después verificamos el contenido
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            # Búsqueda de bytes nulos que indican archivo binario
            if b'\x00' in chunk:
                return True

            # Intenta decodificar como texto
            try:
                chunk.decode('utf-8')
                return False
            except UnicodeDecodeError:
                return True
    except Exception:
        return True

def should_skip_file(file_path):
    """Determine if a file should be skipped."""
    try:
        file_name = os.path.basename(file_path)
        ext = os.path.splitext(file_name)[1].lower()

        # Skip by extension
        if ext in IGNORED_EXTENSIONS:
            return True

        # Skip by filename
        if file_name in IGNORED_FILES:
            return True

        # Skip by file size
        if get_file_size_mb(file_path) > MAX_FILE_SIZE_MB:
            return True

        # Skip binary files
        if is_binary_file(file_path):
            return True

        # Skip large files by line count
        line_count = count_lines(file_path)
        if line_count > MAX_LINE_COUNT:
            return True

        return False
    except Exception as e:
        print(f"Error checking file {file_path}: {e}")
        return True

def should_skip_dir(dir_path):
    """Determine if a directory should be skipped."""
    dir_name = os.path.basename(dir_path)
    return dir_name in IGNORED_DIRS

def limit_file_content(file_path, max_lines=1000):
    """Read file content with a limit on lines to avoid memory issues."""
    lines = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append(f"... (file truncated, showing {max_lines} of {count_lines(file_path)} lines)")
                    break
                lines.append(line.rstrip())
        return lines
    except Exception as e:
        return [f"Error reading file: {str(e)}"]

class OutputSizeTracker:
    def __init__(self, max_size_mb=MAX_OUTPUT_SIZE_MB):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.current_size = 0
        self.limit_reached = False

    def write(self, output_file, text):
        if self.limit_reached:
            return False

        # Comprueba el tamaño antes de escribir
        text_bytes = text.encode('utf-8')
        self.current_size += len(text_bytes)

        if self.current_size > self.max_size_bytes:
            output_file.write("\n\n¡ADVERTENCIA! Límite de tamaño de archivo de salida alcanzado.\n")
            output_file.write(f"El archivo de salida se ha truncado a aproximadamente {MAX_OUTPUT_SIZE_MB} MB para evitar problemas de memoria.\n")
            self.limit_reached = True
            return False

        output_file.write(text)
        return True

def find_specific_files(root_path, specific_files=["logback.xml", "pom.xml"]):
    """Find specific files in the directory tree even in ignored directories."""
    found_files = []

    # Walk through ALL directories including ignored ones
    for dirpath, dirnames, filenames in os.walk(root_path):
        for filename in filenames:
            if filename in specific_files:
                file_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(file_path, root_path)
                found_files.append((dirpath, rel_path, filename))

    return found_files

def collect_file_tree_structure(root_path, folders_only=False):
    """Collect file tree structure without content for initial display."""
    tree_structure = []
    processed_dirs = set()  # Para detectar bucles recursivos
    root_path = os.path.abspath(root_path)

    # Encontrar archivos específicos que queremos incluir aunque estén en directorios ignorados
    special_files = find_specific_files(root_path)
    special_paths = {os.path.join(root_path, rel_path) for _, rel_path, _ in special_files}

    # Recolectar directorios padres de los archivos especiales para asegurarnos de mostrarlos
    special_dirs = set()
    for dirpath, rel_path, _ in special_files:
        parts = Path(os.path.relpath(dirpath, root_path)).parts
        for i in range(len(parts)):
            partial_path = os.path.join(root_path, *parts[:i+1])
            special_dirs.add(partial_path)

    # Walk through directory tree to build structure
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Verificar si ya procesamos este directorio (evitar bucles)
        if dirpath in processed_dirs:
            continue
        processed_dirs.add(dirpath)

        # Skip ignored directories unless they contain special files
        original_dirnames = dirnames.copy()
        dirnames[:] = [d for d in dirnames if not should_skip_dir(os.path.join(dirpath, d))
                      or os.path.join(dirpath, d) in special_dirs]

        # Calculate relative path
        rel_path = os.path.relpath(dirpath, root_path)
        if rel_path == '.':
            rel_path = ''

        # Calculate depth level for indentation
        level = 0 if rel_path == '' else rel_path.count(os.sep) + 1
        indent = '│   ' * level

        # Add directory name to structure
        if rel_path != '':
            dir_name = os.path.basename(dirpath)
            tree_structure.append(f"{indent[:-4]}{'└── ' if level > 0 else '├── '}📂 {dir_name}")

        # Process files within this directory
        # Si estamos en el directorio raíz y folders_only=True, saltamos los archivos
        if folders_only and rel_path == '':
            continue

        sorted_files = sorted(filenames)
        for i, filename in enumerate(sorted_files):
            file_path = os.path.join(dirpath, filename)

            # Incluir archivos especiales siempre (excepto en raíz con folders_only=True)
            is_special = file_path in special_paths or filename in ["logback.xml", "pom.xml"]

            # En el directorio raíz con folders_only=True, incluir SOLO archivos especiales
            if folders_only and rel_path == '' and not is_special:
                continue

            # Skip files according to rules unless they are special files
            if should_skip_file(file_path) and not is_special:
                continue

            # Get relative file path from root
            rel_file_path = os.path.relpath(file_path, root_path)

            # Add file to structure
            is_last = (i == len(sorted_files) - 1)
            tree_structure.append(f"{indent}{'└── ' if is_last else '├── '}📄 {rel_file_path}")

    return tree_structure

def generate_file_tree(root_path, output_file, include_content=True, verbosity=1, folders_only=False):
    """Generate a tree structure showing file paths relative to the root."""
    processed_dirs = set()  # Para detectar bucles recursivos
    root_path = os.path.abspath(root_path)

    # Inicializar tracker de tamaño
    size_tracker = OutputSizeTracker()

    # Primero, recopilamos la estructura completa del árbol
    tree_structure = collect_file_tree_structure(root_path, folders_only=folders_only)

    # Escribimos el encabezado con información del proyecto
    project_name = os.path.basename(root_path)
    title = f"ESTRUCTURA COMPLETA DE ARCHIVOS: {project_name}"
    if folders_only:
        title += " (SOLO CARPETAS)"

    size_tracker.write(output_file, f"{title}\n")
    size_tracker.write(output_file, f"{'=' * 80}\n\n")

    # Escribimos la estructura completa del árbol primero
    for line in tree_structure:
        if not size_tracker.write(output_file, f"{line}\n"):
            return

    # Escribimos un separador entre la estructura y el contenido detallado
    size_tracker.write(output_file, f"\n\nCONTENIDO DETALLADO DE LOS ARCHIVOS\n")
    size_tracker.write(output_file, f"{'=' * 80}\n\n")

    # Walk through directory tree for detailed content
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Verificar si ya procesamos este directorio (evitar bucles)
        if dirpath in processed_dirs:
            continue
        processed_dirs.add(dirpath)

        # Skip ignored directories
        dirnames[:] = [d for d in dirnames if not should_skip_dir(os.path.join(dirpath, d))]

        # Calculate relative path
        rel_path = os.path.relpath(dirpath, root_path)
        if rel_path == '.':
            rel_path = ''

        # Calculate depth level for indentation
        level = 0 if rel_path == '' else rel_path.count(os.sep) + 1
        indent = '│   ' * level

        # Print directory name
        if rel_path != '':
            dir_name = os.path.basename(dirpath)
            if not size_tracker.write(output_file, f"{indent[:-4]}{'└── ' if level > 0 else '├── '}📂 {dir_name}\n"):
                return

        # Process files within this directory
        sorted_files = sorted(filenames)
        for i, filename in enumerate(sorted_files):
            file_path = os.path.join(dirpath, filename)

            # Manejar especialmente logback.xml
            is_logback = filename == "logback.xml"

            # Skip files according to rules (except logback.xml)
            if should_skip_file(file_path) and not is_logback:
                if verbosity > 1:  # Only show skipped files in higher verbosity
                    rel_file_path = os.path.relpath(file_path, root_path)
                    if not size_tracker.write(output_file, f"{indent}{'└── ' if i == len(sorted_files) - 1 else '├── '}🔶 {rel_file_path} (skipped)\n"):
                        return
                continue

            # Get relative file path from root
            rel_file_path = os.path.relpath(file_path, root_path)

            # Print file name with full path
            is_last = (i == len(sorted_files) - 1)
            if not size_tracker.write(output_file, f"{indent}{'└── ' if is_last else '├── '}📄 {rel_file_path}\n"):
                return

            # Include file content if requested and file is not too large (or is logback.xml)
            if include_content:
                content_indent = indent + ('    ' if is_last else '│   ')

                # Verificar nuevamente el tamaño del archivo (excepto logback.xml)
                if get_file_size_mb(file_path) > MAX_FILE_SIZE_MB and not is_logback:
                    if not size_tracker.write(output_file, f"{content_indent}(Archivo demasiado grande para mostrar contenido: {get_file_size_mb(file_path):.2f} MB)\n"):
                        return
                    continue

                # Agregar separador de inicio de contenido
                if not size_tracker.write(output_file, f"{content_indent}────── CONTENIDO DEL ARCHIVO ──────\n"):
                    return

                # Leer contenido con límite (sin límite para logback.xml)
                max_lines = None if is_logback else MAX_LINE_COUNT
                content_lines = limit_file_content(file_path, max_lines=max_lines)
                for line in content_lines:
                    if not size_tracker.write(output_file, f"{content_indent}{line}\n"):
                        return

                # Agregar separador de fin de contenido
                if not size_tracker.write(output_file, f"{content_indent}────── FIN DEL ARCHIVO ──────\n"):
                    return

def get_available_folders(base_path=None):
    """
    Detecta las carpetas disponibles en la ruta base proporcionada.
    Si no se proporciona una ruta, usa el directorio actual.
    """
    if base_path is None:
        base_path = os.getcwd()

    folders = []
    try:
        # Obtener todas las entradas en el directorio
        entries = os.listdir(base_path)

        # Filtrar solo las carpetas
        folders = [entry for entry in entries if os.path.isdir(os.path.join(base_path, entry))
                   and not entry.startswith('.')
                   and entry not in IGNORED_DIRS]
    except Exception as e:
        print(f"Error al listar carpetas: {e}")

    return folders

def show_folder_selection_menu(folders):
    """
    Muestra un menú para seleccionar la carpeta a procesar.
    """
    print("\n=== Carpetas disponibles ===")

    if not folders:
        print("No se encontraron carpetas para procesar.")
        return None

    # Imprimir las opciones disponibles
    for i, folder in enumerate(folders, 1):
        print(f"{i}. {folder}")
    print(f"{len(folders) + 1}. Procesar directorio actual completo (SOLO CARPETAS)")
    print(f"{len(folders) + 2}. Procesar directorio actual completo (INCLUIR ARCHIVOS DE RAÍZ)")
    print("0. Salir")

    # Solicitar selección
    while True:
        try:
            choice = input("\nSeleccione una carpeta (número): ")
            if choice == "0":
                return None

            choice = int(choice)
            if 1 <= choice <= len(folders):
                return folders[choice - 1]
            elif choice == len(folders) + 1:
                return "."  # Procesar solo carpetas
            elif choice == len(folders) + 2:
                return ".+"  # Procesar todo (carpetas + archivos de raíz)
            else:
                print("Opción inválida. Intente de nuevo.")
        except ValueError:
            print("Por favor, ingrese un número válido.")

def main():
    parser = argparse.ArgumentParser(description='Generate a clean code structure report.')
    parser.add_argument('path', nargs='?', default=None, help='Root directory path (default: interactive selection)')
    parser.add_argument('-o', '--output', help='Output file name (default: code_structure_TIMESTAMP.txt)')
    parser.add_argument('-s', '--structure-only', action='store_true', help='Only show structure without file content')
    parser.add_argument('-v', '--verbosity', type=int, choices=[1, 2, 3], default=1,
                        help='Verbosity level: 1=basic, 2=show skipped, 3=full (default: 1)')
    parser.add_argument('-i', '--interactive', action='store_true', help='Force interactive folder selection')
    parser.add_argument('--root-files', action='store_true', help='Include files in root directory when processing all folders')

    # Declare global before using it
    global MAX_OUTPUT_SIZE_MB

    parser.add_argument('-m', '--max-output', type=int, default=MAX_OUTPUT_SIZE_MB,
                        help=f'Maximum output file size in MB (default: {MAX_OUTPUT_SIZE_MB})')

    args = parser.parse_args()

    # Actualizar el límite de tamaño de salida si se especificó
    MAX_OUTPUT_SIZE_MB = args.max_output

    # Obtener la ruta a procesar
    process_path = args.path
    # Flag para procesar solo carpetas (sin archivos de la raíz)
    process_folders_only = False

    # Si no se especificó una ruta o se solicitó modo interactivo
    if process_path is None or args.interactive:
        print("=== Generador de estructura de código ===")
        # Obtener las carpetas disponibles
        available_folders = get_available_folders()
        # Mostrar menú de selección
        selected_folder = show_folder_selection_menu(available_folders)

        if selected_folder is None:
            print("Operación cancelada.")
            return

        # Si seleccionó procesar directorio actual completo, solo procesar carpetas
        if selected_folder == ".":
            process_folders_only = True

        # Construir la ruta completa
        process_path = os.path.join(os.getcwd(), selected_folder)
    else:
        # Si se proporcionó una ruta, usarla directamente
        process_path = os.path.abspath(process_path)

    # Set output filename
    folder_name = os.path.basename(process_path) if process_path != os.getcwd() else "root"

    # Si se eligió ".+" para incluir archivos de la raíz
    if process_path.endswith('.+'):
        process_path = process_path[:-1]  # Quitar el + del final
        process_folders_only = False

    if args.output:
        output_filename = args.output
    else:
        output_filename = f"code_structure_{folder_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    print(f"\nGenerating code structure for: {process_path}")
    print(f"Output will be saved to: {output_filename}")
    print(f"Verbosity level: {args.verbosity}")
    print(f"Maximum output file size: {MAX_OUTPUT_SIZE_MB} MB")

    if process_folders_only:
        print("Processing only folders (ignoring files in root directory)")

    if args.structure_only:
        print("File content will NOT be included")
    else:
        print("File content will be included")

    with open(output_filename, 'w', encoding='utf-8') as output_file:
        # Call the function to generate the tree
        generate_file_tree(process_path, output_file, include_content=not args.structure_only,
                          verbosity=args.verbosity, folders_only=process_folders_only)

    # Verificar el tamaño final del archivo
    final_size_mb = os.path.getsize(output_filename) / (1024 * 1024)
    print(f"\nCode structure successfully generated to {output_filename} (Size: {final_size_mb:.2f} MB)")

if __name__ == "__main__":
    main()
