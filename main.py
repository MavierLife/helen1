#!/usr/bin/env python3
import os
import json
import subprocess
import sys

# —————— CONFIGURACIÓN ——————
HOST               = 'localhost'            # ← host de tu servidor MySQL
PORT               = 3306
USER               = 'root'
PASSWORD           = ''
DB_NAME            = 'helensystem_data'     # ← la BD que quieres copiar
BACKUP_DIR         = r'C:\ruta\de\backup'
BACKUP_FILE_NAME   = 'backup.sql'
STATE_FILE_NAME    = 'backup.state.json'

# Detectar automáticamente la ruta de herramientas MySQL
def get_mysql_bin_dir():
    # Rutas posibles de MySQL
    possible_paths = [
        r'C:\Program Files\MySQL\MySQL Server 8.0\bin',
        r'C:\xampp\mysql\bin'
    ]
    
    for path in possible_paths:
        if os.path.exists(path) and os.path.exists(os.path.join(path, 'mysql.exe')):
            print(f"Usando MySQL desde: {path}")
            return path
    
    # Si no encuentra ninguna ruta, mostrar error
    print("ERROR: No se encontró MySQL en las rutas esperadas:", file=sys.stderr)
    for path in possible_paths:
        print(f"  - {path}", file=sys.stderr)
    sys.exit(1)

MYSQL_BIN_DIR      = get_mysql_bin_dir()
MYSQL_CMD          = os.path.join(MYSQL_BIN_DIR, 'mysql.exe')
MYSQLDUMP_CMD      = os.path.join(MYSQL_BIN_DIR, 'mysqldump.exe')
MYSQLBINLOG_CMD    = os.path.join(MYSQL_BIN_DIR, 'mysqlbinlog.exe')
# ——————————————————————————

def run(cmd):
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"ERROR ejecutando {' '.join(cmd)}:\n{res.stderr}", file=sys.stderr)
        sys.exit(1)
    return res.stdout

def get_master_status(config):
    """Obtener el estado actual del master"""
    mysql_cmd = os.path.join(MYSQL_BIN_DIR, 'mysql.exe')
    cmd = [
        mysql_cmd,
        "-h", config['HOST'], "-P", str(config['PORT']),
        "-u", config['USER'], f"-p{config['PASSWORD']}",
        "-e", "SHOW MASTER STATUS\\G"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    
    for line in result.stdout.split('\n'):
        if 'File:' in line:
            file_ = line.split(': ')[1].strip()
        if 'Position:' in line:
            pos = int(line.split(': ')[1].strip())
    return file_, pos

def full_backup(backup_file, config):
    """Realizar backup completo de la base de datos"""
    print("-> Generando backup completo de", config['DB_NAME'])
    cmd = [
        MYSQLDUMP_CMD,
        "-h", config['HOST'], "-P", str(config['PORT']),
        "-u", config['USER'], f"-p{config['PASSWORD']}",
        "--single-transaction",
        "--routines",
        "--triggers",
        "--set-gtid-purged=OFF",
        config['DB_NAME']
    ]
    with open(backup_file, "w", encoding="utf-8") as f:
        subprocess.run(cmd, stdout=f, check=True)
    print(f"Backup completo guardado en {backup_file}")

def incremental_backup(backup_file, state, config):
    """Realizar backup incremental usando binlogs"""
    print(f"-> Exportando binlogs de {config['DB_NAME']} desde {state['File']}@{state['Position']}…")
    cmd = [
        MYSQLBINLOG_CMD,
        "--skip-gtids",
        "-h", config['HOST'], "-P", str(config['PORT']),
        "-u", config['USER'], f"-p{config['PASSWORD']}",
        "--read-from-remote-server",
        f"--start-position={state['Position']}",
        f"--database={config['DB_NAME']}",
        state["File"]
    ]
    with open(backup_file, "a", encoding="utf-8") as f:
        subprocess.run(cmd, stdout=f, check=True)
    print(f"Incremental añadido a {backup_file}")

def load_state(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_state(path, file_, pos):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"File": file_, "Position": pos}, f)

def main(config=None):
    # Usar configuración pasada como parámetro o valores por defecto
    if config is None:
        config = {
            'HOST': HOST,
            'PORT': PORT,
            'USER': USER,
            'PASSWORD': PASSWORD,
            'DB_NAME': DB_NAME,
            'BACKUP_DIR': BACKUP_DIR
        }
    
    os.makedirs(config['BACKUP_DIR'], exist_ok=True)
    backup_file = os.path.join(config['BACKUP_DIR'], BACKUP_FILE_NAME)
    state_file  = os.path.join(config['BACKUP_DIR'], STATE_FILE_NAME)

    # Verificar si existe el archivo de backup además del estado
    backup_exists = os.path.exists(backup_file)
    state = load_state(state_file)
    
    # Si no existe el backup o no hay estado, hacer backup completo
    if state is None or not backup_exists:
        if not backup_exists:
            print("No se encontró backup previo, generando backup completo...")
        else:
            print("No se encontró estado previo, regenerando backup completo...")
        
        full_backup(backup_file, config)
        file_, pos = get_master_status(config)
        save_state(state_file, file_, pos)
        print(f"Estado inicial guardado: {file_}@{pos}")
    else:
        # Existe tanto el backup como el estado, hacer incremental
        print("Backup previo encontrado, realizando backup incremental...")
        incremental_backup(backup_file, state, config)
        file_, pos = get_master_status(config)
        save_state(state_file, file_, pos)
        print(f"Estado actualizado a: {file_}@{pos}")

if __name__ == "__main__":
    main()