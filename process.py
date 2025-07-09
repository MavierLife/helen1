import os
import time
import threading
import schedule
from datetime import datetime, timedelta
import shutil
import json
import subprocess
from pathlib import Path

class NightlyProcessor:
    def __init__(self, config):
        """
        Procesador nocturno para dividir y organizar backups
        
        Args:
            config (dict): Configuración con las siguientes claves:
                - BACKUP_DIR: Directorio temporal donde main.py guarda los backups
                - DAILY_BACKUP_DIR: Directorio para almacenar backups diarios organizados
                - MAX_FILE_SIZE_GB: Tamaño máximo por archivo dividido (default: 1)
                - SPLIT_TIME: Hora de corte en formato "HH:MM" (default: "00:00")
                - BACKUP_FILE_NAME: Nombre del archivo de backup (default: "backup.sql")
                - STATE_FILE_NAME: Nombre del archivo de estado (default: "backup.state.json")
        """
        self.config = config
        self.is_running = False
        self.scheduler_thread = None
        
        # Configuración por defecto
        self.max_file_size_gb = config.get('MAX_FILE_SIZE_GB', 1)
        self.split_time = config.get('SPLIT_TIME', "00:00")
        self.backup_file_name = config.get('BACKUP_FILE_NAME', 'backup.sql')
        self.state_file_name = config.get('STATE_FILE_NAME', 'backup.state.json')
        
        # Directorios
        self.backup_dir = config['BACKUP_DIR']
        self.daily_backup_dir = config.get('DAILY_BACKUP_DIR', 
                                          os.path.join(config['BACKUP_DIR'], 'daily_backups'))
        
        # Crear directorios necesarios
        os.makedirs(self.daily_backup_dir, exist_ok=True)
        
        # Referencias para controlar el proceso principal
        self.main_process_controller = None
        
        print(f"🌙 Procesador nocturno configurado para las {self.split_time}")
        print(f"📦 Tamaño máximo por archivo: {self.max_file_size_gb} GB")
        print(f"📁 Directorio temporal: {self.backup_dir}")
        print(f"📂 Directorio diario: {self.daily_backup_dir}")
    
    def set_main_controller(self, controller):
        """
        Establecer referencia al controlador del proceso principal (UI o scheduler externo)
        
        Args:
            controller: Objeto que debe tener métodos:
                - stop_automatic_backup(): Para detener el proceso automático
                - start_automatic_backup(): Para reiniciar el proceso automático  
                - is_backup_in_progress(): Para verificar si hay backup en curso
        """
        self.main_process_controller = controller
        print("🔗 Controlador principal vinculado al procesador nocturno")
    
    def start_nightly_processor(self):
        """Iniciar el procesador nocturno"""
        if self.is_running:
            print("⚠️ El procesador nocturno ya está en ejecución")
            return
        
        self.is_running = True
        
        # Programar la tarea de división a la hora especificada
        schedule.clear()
        schedule.every().day.at(self.split_time).do(self._nightly_process)
        
        # Iniciar hilo del programador
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        print(f"🚀 Procesador nocturno iniciado. División programada para las {self.split_time}")
    
    def stop_nightly_processor(self):
        """Detener el procesador nocturno"""
        self.is_running = False
        schedule.clear()
        print("🛑 Procesador nocturno detenido")
    
    def force_nightly_process(self):
        """Forzar el proceso nocturno manualmente (para pruebas)"""
        print("🔧 Ejecutando proceso nocturno manualmente...")
        threading.Thread(target=self._nightly_process, daemon=True).start()
    
    def _run_scheduler(self):
        """Ejecutar el programador en un hilo separado"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # Verificar cada minuto
    
    def _nightly_process(self):
        """Proceso principal que se ejecuta en el horario programado"""
        print(f"🌙 === INICIANDO PROCESO NOCTURNO ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===")
        
        try:
            # 1. Verificar si hay un proceso de copia incremental en curso
            self._wait_for_backup_completion()
            
            # 2. Detener el proceso automático de copias
            was_running = self._stop_main_process()
            
            # 3. Procesar el archivo .sql de backup completo del día
            success = self._process_daily_backup()
            
            if success:
                # 4. Vaciar la carpeta temporal
                self._clean_temp_directory()
                
                # 5. Generar nuevo volcado completo y reiniciar proceso
                self._initialize_new_cycle(was_running)

                # 6. Limpiar la copia de seguridad del día anterior
                self._clean_previous_day_backup()
                
                print("🎉 === PROCESO NOCTURNO COMPLETADO EXITOSAMENTE ===")
            else:
                print("⚠️ === PROCESO NOCTURNO COMPLETADO CON ERRORES ===")
                # Reiniciar el proceso principal aunque haya habido errores
                if was_running:
                    self._restart_main_process()
                    
        except Exception as e:
            print(f"🔥 ERROR CRÍTICO EN PROCESO NOCTURNO: {e}")
            # Intentar reiniciar el proceso principal en caso de error
            try:
                if self.main_process_controller:
                    self.main_process_controller.start_automatic_backup()
            except:
                pass
    
    def _wait_for_backup_completion(self):
        """Esperar a que termine cualquier backup en progreso"""
        if not self.main_process_controller:
            print("⚠️ No hay controlador principal vinculado, continuando...")
            return
        
        if hasattr(self.main_process_controller, 'is_backup_in_progress'):
            if self.main_process_controller.is_backup_in_progress():
                print("⏳ Esperando a que termine el backup en progreso...")
                timeout = 600  # 10 minutos máximo
                waited = 0
                
                while self.main_process_controller.is_backup_in_progress() and waited < timeout:
                    time.sleep(10)
                    waited += 10
                    print(f"⏳ Esperando... ({waited}/{timeout} segundos)")
                
                if self.main_process_controller.is_backup_in_progress():
                    print("⚠️ Timeout esperando backup, continuando de todas formas...")
                else:
                    print("✅ Backup completado, continuando...")
        else:
            print("ℹ️ No se puede verificar estado del backup, esperando 30 segundos...")
            time.sleep(30)
    
    def _stop_main_process(self):
        """Detener el proceso automático de copias"""
        was_running = False
        
        if self.main_process_controller:
            try:
                # Verificar si estaba ejecutándose
                if hasattr(self.main_process_controller, 'is_running'):
                    was_running = self.main_process_controller.is_running
                
                # Detener el proceso
                if hasattr(self.main_process_controller, 'stop_automatic_backup'):
                    self.main_process_controller.stop_automatic_backup()
                    print("⏹️ Proceso automático de backups detenido")
                    time.sleep(5)  # Dar tiempo para que se detenga completamente
                
            except Exception as e:
                print(f"⚠️ Error al detener proceso principal: {e}")
        else:
            print("⚠️ No hay controlador principal vinculado")
        
        return was_running
    
    def _restart_main_process(self):
        """Reiniciar el proceso automático de copias"""
        if self.main_process_controller:
            try:
                if hasattr(self.main_process_controller, 'start_automatic_backup'):
                    self.main_process_controller.start_automatic_backup()
                    print("🚀 Proceso automático de backups reiniciado")
            except Exception as e:
                print(f"❌ Error al reiniciar proceso principal: {e}")
    
    def _process_daily_backup(self):
        """Procesar el archivo de backup del día actual"""
        backup_file = os.path.join(self.backup_dir, self.backup_file_name)
        
        if not os.path.exists(backup_file):
            print(f"❌ No se encontró archivo de backup: {backup_file}")
            return False
        
        # Calcular la fecha del día anterior (ya que estamos en 00:00 del día siguiente)
        yesterday = datetime.now() - timedelta(days=1)
        folder_name = yesterday.strftime("%Y-%m-%d_%H-%M")
        daily_folder = os.path.join(self.daily_backup_dir, folder_name)
        
        print(f"📦 Procesando backup del día: {yesterday.strftime('%Y-%m-%d')}")
        print(f"📁 Carpeta destino: {daily_folder}")
        
        # Crear carpeta del día
        try:
            os.makedirs(daily_folder, exist_ok=True)
        except Exception as e:
            print(f"❌ Error al crear carpeta diaria: {e}")
            return False
        
        # Dividir el archivo
        split_files = self._split_backup_file(backup_file, daily_folder)
        
        if split_files:
            # Verificar que la división fue exitosa
            if self._verify_split_files(backup_file, split_files):
                print(f"✅ Backup dividido exitosamente en {len(split_files)} archivos")
                
                # Crear archivo de información
                self._create_info_file(daily_folder, split_files, yesterday)
                return True
            else:
                print("❌ Error en la verificación de archivos divididos")
                return False
        else:
            print("❌ Error al dividir el archivo de backup")
            return False
    
    def _split_backup_file(self, source_file, target_folder):
        """Dividir el archivo de backup en partes más pequeñas"""
        try:
            file_size = os.path.getsize(source_file)
            max_size_bytes = self.max_file_size_gb * 1024 * 1024 * 1024  # GB a bytes
            
            print(f"📄 Archivo origen: {os.path.basename(source_file)}")
            print(f"📏 Tamaño: {file_size / (1024**3):.2f} GB")
            
            if file_size <= max_size_bytes:
                # Si el archivo es menor al tamaño máximo, solo copiarlo
                target_file = os.path.join(target_folder, "backup_part_001.sql")
                shutil.copy2(source_file, target_file)
                print(f"📄 Archivo copiado (sin división): {os.path.basename(target_file)}")
                return [target_file]
            
            print(f"✂️ Dividiendo en partes de {self.max_file_size_gb} GB máximo...")
            
            split_files = []
            part_num = 1
            
            with open(source_file, 'rb') as source:
                while True:
                    part_filename = os.path.join(target_folder, f"backup_part_{part_num:03d}.sql")
                    
                    with open(part_filename, 'wb') as part_file:
                        bytes_written = 0
                        
                        while bytes_written < max_size_bytes:
                            chunk_size = min(1024 * 1024, max_size_bytes - bytes_written)  # 1MB chunks
                            chunk = source.read(chunk_size)
                            
                            if not chunk:
                                break
                            
                            part_file.write(chunk)
                            bytes_written += len(chunk)
                    
                    if bytes_written > 0:
                        split_files.append(part_filename)
                        size_mb = bytes_written / (1024**2)
                        print(f"📄 Parte {part_num:03d}: {os.path.basename(part_filename)} ({size_mb:.1f} MB)")
                        part_num += 1
                    
                    if bytes_written < max_size_bytes:
                        break
            
            return split_files
            
        except Exception as e:
            print(f"❌ Error al dividir archivo: {e}")
            return []
    
    def _verify_split_files(self, original_file, split_files):
        """Verificar que los archivos divididos son válidos"""
        try:
            original_size = os.path.getsize(original_file)
            total_split_size = sum(os.path.getsize(f) for f in split_files if os.path.exists(f))
            
            print(f"🔍 Verificando integridad...")
            print(f"📏 Tamaño original: {original_size:,} bytes")
            print(f"📏 Suma de partes: {total_split_size:,} bytes")
            
            if original_size != total_split_size:
                print(f"❌ ERROR: Los tamaños no coinciden")
                return False
            
            # Verificar que todos los archivos existen
            for split_file in split_files:
                if not os.path.exists(split_file):
                    print(f"❌ ERROR: Archivo no existe: {os.path.basename(split_file)}")
                    return False
            
            print("✅ Verificación de integridad exitosa")
            return True
            
        except Exception as e:
            print(f"❌ Error en verificación: {e}")
            return False
    
    def _create_info_file(self, folder_path, split_files, backup_date):
        """Crear archivo de información sobre el backup"""
        try:
            info = {
                "backup_date": backup_date.strftime("%Y-%m-%d"),
                "creation_time": datetime.now().isoformat(),
                "total_files": len(split_files),
                "max_file_size_gb": self.max_file_size_gb,
                "files": [
                    {
                        "filename": os.path.basename(f),
                        "size_bytes": os.path.getsize(f),
                        "size_mb": round(os.path.getsize(f) / (1024**2), 2)
                    }
                    for f in split_files if os.path.exists(f)
                ],
                "total_size_gb": round(sum(os.path.getsize(f) for f in split_files if os.path.exists(f)) / (1024**3), 2),
                "backup_config": {
                    "backup_dir": self.backup_dir,
                    "daily_backup_dir": self.daily_backup_dir,
                    "split_time": self.split_time
                }
            }
            
            info_file = os.path.join(folder_path, "backup_info.json")
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2, ensure_ascii=False)
            
            print(f"📋 Archivo de información creado: backup_info.json")
            
        except Exception as e:
            print(f"⚠️ Error al crear archivo de información: {e}")
    
    def _clean_previous_day_backup(self):
        """Eliminar la carpeta de backup del día anterior al procesado."""
        try:
            # La copia procesada es de 'ayer', por lo que buscamos la de 'anteayer'
            day_to_delete = datetime.now() - timedelta(days=2)
            
            # Listar todas las carpetas en el directorio de backups diarios
            subfolders = [f.path for f in os.scandir(self.daily_backup_dir) if f.is_dir()]
            
            for folder_path in subfolders:
                folder_name = os.path.basename(folder_path)
                try:
                    # Intentar parsear el nombre de la carpeta para ver si coincide con la fecha a eliminar
                    folder_date = datetime.strptime(folder_name.split('_')[0], "%Y-%m-%d")
                    if folder_date.date() == day_to_delete.date():
                        print(f"🗑️ Eliminando backup antiguo: {folder_name}")
                        shutil.rmtree(folder_path)
                        print(f"✅ Carpeta de backup antigua eliminada: {folder_name}")
                except (ValueError, IndexError):
                    # Ignorar carpetas que no coinciden con el formato de fecha esperado
                    continue
                    
        except Exception as e:
            print(f"⚠️ Error al eliminar la carpeta de backup del día anterior: {e}")

    def _clean_temp_directory(self):
        """Limpiar el directorio temporal de backups"""
        try:
            backup_file = os.path.join(self.backup_dir, self.backup_file_name)
            state_file = os.path.join(self.backup_dir, self.state_file_name)
            
            files_removed = 0
            
            if os.path.exists(backup_file):
                os.remove(backup_file)
                files_removed += 1
                print(f"🗑️ Eliminado: {self.backup_file_name}")
            
            if os.path.exists(state_file):
                os.remove(state_file)
                files_removed += 1
                print(f"🗑️ Eliminado: {self.state_file_name}")
            
            if files_removed > 0:
                print(f"🧹 Directorio temporal limpiado ({files_removed} archivos)")
            else:
                print("ℹ️ No había archivos temporales para limpiar")
                
        except Exception as e:
            print(f"⚠️ Error al limpiar directorio temporal: {e}")
    
    def _initialize_new_cycle(self, restart_automatic=True):
        """Inicializar un nuevo ciclo de backup"""
        try:
            # Importar main aquí para evitar dependencias circulares
            import main
            
            backup_file = os.path.join(self.backup_dir, self.backup_file_name)
            state_file = os.path.join(self.backup_dir, self.state_file_name)
            
            print("🔄 Generando nuevo backup completo para iniciar ciclo...")
            
            # Crear configuración para main.py
            main_config = {
                'HOST': self.config.get('HOST', 'localhost'),
                'PORT': self.config.get('PORT', 3306),
                'USER': self.config.get('USER', 'root'),
                'PASSWORD': self.config.get('PASSWORD', ''),
                'DB_NAME': self.config.get('DB_NAME', ''),
                'BACKUP_DIR': self.backup_dir
            }
            
            # Ejecutar backup completo
            main.full_backup(backup_file, main_config)
            
            # Obtener y guardar estado inicial
            file_, pos = main.get_master_status(main_config)
            main.save_state(state_file, file_, pos)
            
            print(f"✅ Nuevo ciclo inicializado. Estado: {file_}@{pos}")
            
            # Reiniciar proceso automático si estaba corriendo
            if restart_automatic:
                self._restart_main_process()
            
        except Exception as e:
            print(f"❌ Error al inicializar nuevo ciclo: {e}")
            # Intentar reiniciar el proceso automático aunque haya error
            if restart_automatic:
                self._restart_main_process()
    
    def get_status(self):
        """Obtener estado actual del procesador"""
        return {
            "is_running": self.is_running,
            "split_time": self.split_time,
            "max_file_size_gb": self.max_file_size_gb,
            "backup_dir": self.backup_dir,
            "daily_backup_dir": self.daily_backup_dir,
            "next_run": self._get_next_run_time()
        }
    
    def _get_next_run_time(self):
        """Calcular próxima ejecución programada"""
        if not self.is_running:
            return None
        
        now = datetime.now()
        split_hour, split_minute = map(int, self.split_time.split(':'))
        
        next_run = now.replace(hour=split_hour, minute=split_minute, second=0, microsecond=0)
        
        # Si ya pasó la hora de hoy, programar para mañana
        if next_run <= now:
            next_run += timedelta(days=1)
        
        return next_run.strftime("%Y-%m-%d %H:%M:%S")

def create_nightly_processor(backup_config, split_config=None):
    """
    Crear un procesador nocturno desde configuración
    
    Args:
        backup_config (dict): Configuración base que incluye BACKUP_DIR
        split_config (dict, optional): Configuración específica para división:
            - MAX_FILE_SIZE_GB: Tamaño máximo por archivo (default: 1)
            - SPLIT_TIME: Hora de división (default: "00:00")
            - DAILY_BACKUP_DIR: Directorio para backups diarios
    """
    config = backup_config.copy()
    
    if split_config:
        config.update(split_config)
    
    # Configuraciones por defecto
    if 'MAX_FILE_SIZE_GB' not in config:
        config['MAX_FILE_SIZE_GB'] = 1
    
    if 'SPLIT_TIME' not in config:
        config['SPLIT_TIME'] = "00:00"
    
    if 'DAILY_BACKUP_DIR' not in config:
        config['DAILY_BACKUP_DIR'] = os.path.join(
            config['BACKUP_DIR'], 'daily_backups'
        )
    
    return NightlyProcessor(config)

if __name__ == "__main__":
    # Ejemplo de uso independiente para pruebas
    config = {
        'HOST': 'localhost',
        'PORT': 3306,
        'USER': 'root',
        'PASSWORD': '',
        'DB_NAME': 'helensystem_data',
        'BACKUP_DIR': r'C:\temp\backup',
        'MAX_FILE_SIZE_GB': 1,
        'SPLIT_TIME': "00:01"  # Para prueba inmediata
    }
    
    processor = NightlyProcessor(config)
    
    try:
        processor.start_nightly_processor()
        print("Presiona Ctrl+C para detener...")
        print("O escribe 'test' para ejecutar proceso nocturno manualmente...")
        
        while True:
            user_input = input().strip().lower()
            if user_input == 'test':
                processor.force_nightly_process()
            elif user_input == 'quit':
                break
            
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo procesador nocturno...")
        processor.stop_nightly_processor()