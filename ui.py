import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import time
import os
import sys
from datetime import datetime
import queue
import json
import main  # Importamos nuestro módulo principal

class BackupUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Helen System - Backup Automático de MySQL")
        self.root.geometry("900x700")
        
        # Variables para configuración de BD
        self.host_var = tk.StringVar(value=main.HOST)
        self.port_var = tk.StringVar(value=str(main.PORT))
        self.user_var = tk.StringVar(value=main.USER)
        self.password_var = tk.StringVar(value=main.PASSWORD)
        self.db_name_var = tk.StringVar(value=main.DB_NAME)
        self.backup_dir_var = tk.StringVar(value=main.BACKUP_DIR)
        
        # Variables para interfaz
        self.interval_hours = tk.StringVar(value="24")
        self.interval_minutes = tk.StringVar(value="0")
        self.is_running = False
        self.backup_thread = None
        
        # Cola para mensajes entre hilos
        self.log_queue = queue.Queue()
        
        self.setup_ui()
        self.check_log_queue()
        self.load_config()  # Cargar configuración guardada si existe
        
    def setup_ui(self):
        # Frame principal con scrollbar
        canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Título
        title_label = ttk.Label(scrollable_frame, text="Helen System - Backup Automático de MySQL", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(10, 20))
        
        # ========== CONFIGURACIÓN DE BASE DE DATOS ==========
        config_frame = ttk.LabelFrame(scrollable_frame, text="Configuración de Base de Datos", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Host
        host_frame = ttk.Frame(config_frame)
        host_frame.pack(fill=tk.X, pady=2)
        ttk.Label(host_frame, text="Host:", width=15).pack(side=tk.LEFT)
        ttk.Entry(host_frame, textvariable=self.host_var, width=30).pack(side=tk.LEFT, padx=(5, 0))
        
        # Puerto
        port_frame = ttk.Frame(config_frame)
        port_frame.pack(fill=tk.X, pady=2)
        ttk.Label(port_frame, text="Puerto:", width=15).pack(side=tk.LEFT)
        ttk.Entry(port_frame, textvariable=self.port_var, width=30).pack(side=tk.LEFT, padx=(5, 0))
        
        # Usuario
        user_frame = ttk.Frame(config_frame)
        user_frame.pack(fill=tk.X, pady=2)
        ttk.Label(user_frame, text="Usuario:", width=15).pack(side=tk.LEFT)
        ttk.Entry(user_frame, textvariable=self.user_var, width=30).pack(side=tk.LEFT, padx=(5, 0))
        
        # Contraseña
        pass_frame = ttk.Frame(config_frame)
        pass_frame.pack(fill=tk.X, pady=2)
        ttk.Label(pass_frame, text="Contraseña:", width=15).pack(side=tk.LEFT)
        ttk.Entry(pass_frame, textvariable=self.password_var, show="*", width=30).pack(side=tk.LEFT, padx=(5, 0))
        
        # Base de datos
        db_frame = ttk.Frame(config_frame)
        db_frame.pack(fill=tk.X, pady=2)
        ttk.Label(db_frame, text="Base de Datos:", width=15).pack(side=tk.LEFT)
        ttk.Entry(db_frame, textvariable=self.db_name_var, width=30).pack(side=tk.LEFT, padx=(5, 0))
        
        # Directorio de backup
        dir_frame = ttk.Frame(config_frame)
        dir_frame.pack(fill=tk.X, pady=2)
        ttk.Label(dir_frame, text="Dir. Backup:", width=15).pack(side=tk.LEFT)
        ttk.Entry(dir_frame, textvariable=self.backup_dir_var, width=25).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(dir_frame, text="...", width=3, command=self.browse_backup_dir).pack(side=tk.LEFT, padx=(5, 0))
        
        # Botones de configuración
        config_btn_frame = ttk.Frame(config_frame)
        config_btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(config_btn_frame, text="Probar Conexión", command=self.test_connection).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(config_btn_frame, text="Guardar Config", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(config_btn_frame, text="Cargar Config", command=self.load_config).pack(side=tk.LEFT, padx=5)
        
        # ========== CONFIGURACIÓN DE INTERVALO ==========
        interval_frame = ttk.LabelFrame(scrollable_frame, text="Configuración de Backup Automático", padding=10)
        interval_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Label(interval_frame, text="Intervalo de backup:").pack(side=tk.LEFT)
        ttk.Entry(interval_frame, textvariable=self.interval_hours, width=5).pack(side=tk.LEFT, padx=(10, 5))
        ttk.Label(interval_frame, text="horas").pack(side=tk.LEFT)
        ttk.Entry(interval_frame, textvariable=self.interval_minutes, width=5).pack(side=tk.LEFT, padx=(10, 5))
        ttk.Label(interval_frame, text="minutos").pack(side=tk.LEFT)
        
        # ========== ÁREA DE LOGS ==========
        log_frame = ttk.LabelFrame(scrollable_frame, text="Logs del Sistema", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # ========== BOTONES DE CONTROL ==========
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.start_button = ttk.Button(button_frame, text="Iniciar Backup Automático", 
                                      command=self.start_automatic_backup)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(button_frame, text="Detener", 
                                     command=self.stop_automatic_backup, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.manual_button = ttk.Button(button_frame, text="Backup Manual", 
                                       command=self.manual_backup)
        self.manual_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = ttk.Button(button_frame, text="Limpiar Logs", 
                                      command=self.clear_logs)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Configurar canvas y scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Log inicial
        self.add_log("Sistema de backup inicializado")
    
    def browse_backup_dir(self):
        directory = filedialog.askdirectory(initialdir=self.backup_dir_var.get())
        if directory:
            self.backup_dir_var.set(directory)
            self.add_log(f"Carpeta de destino cambiada a: {directory}")
    
    def get_db_config(self):
        """Obtener la configuración actual de la base de datos"""
        return {
            'HOST': self.host_var.get(),
            'PORT': int(self.port_var.get()) if self.port_var.get().isdigit() else 3306,
            'USER': self.user_var.get(),
            'PASSWORD': self.password_var.get(),
            'DB_NAME': self.db_name_var.get(),
            'BACKUP_DIR': self.backup_dir_var.get()
        }
    
    def test_connection(self):
        """Probar la conexión a la base de datos"""
        config = self.get_db_config()
        
        # Validar configuración
        if not all([config['HOST'], config['USER'], config['DB_NAME']]):
            messagebox.showerror("Error", "Por favor complete los campos obligatorios (Host, Usuario, Base de Datos)")
            return
        
        def test_in_thread():
            try:
                import subprocess
                mysql_cmd = os.path.join(main.MYSQL_BIN_DIR, 'mysql.exe')
                cmd = [
                    mysql_cmd,
                    "-h", config['HOST'], "-P", str(config['PORT']),
                    "-u", config['USER']
                ]
                
                if config['PASSWORD']:
                    cmd.append(f"-p{config['PASSWORD']}")
                
                cmd.extend(["-e", "SELECT 'Conexión exitosa' as test"])
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    self.log_queue.put("✓ Conexión exitosa a la base de datos")
                    messagebox.showinfo("Éxito", "¡Conexión exitosa a la base de datos!")
                else:
                    error_msg = result.stderr.strip() if result.stderr else "Error desconocido"
                    self.log_queue.put(f"✗ Error de conexión: {error_msg}")
                    messagebox.showerror("Error", f"Error de conexión:\n{error_msg}")
                    
            except subprocess.TimeoutExpired:
                self.log_queue.put("✗ Timeout en la conexión")
                messagebox.showerror("Error", "Timeout: La conexión tardó demasiado")
            except Exception as e:
                self.log_queue.put(f"✗ Error al probar conexión: {str(e)}")
                messagebox.showerror("Error", f"Error al probar conexión:\n{str(e)}")
        
        self.add_log("Probando conexión a la base de datos...")
        threading.Thread(target=test_in_thread, daemon=True).start()
    
    def save_config(self):
        """Guardar configuración actual"""
        config = self.get_db_config()
        config['interval_hours'] = self.interval_hours.get()
        config['interval_minutes'] = self.interval_minutes.get()
        
        try:
            with open("backup_config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            self.add_log("✓ Configuración guardada en backup_config.json")
            messagebox.showinfo("Éxito", "Configuración guardada correctamente")
        except Exception as e:
            self.add_log(f"✗ Error al guardar configuración: {str(e)}")
            messagebox.showerror("Error", f"Error al guardar configuración:\n{str(e)}")
    
    def load_config(self):
        """Cargar configuración guardada"""
        try:
            if os.path.exists("backup_config.json"):
                with open("backup_config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                self.host_var.set(config.get('HOST', 'localhost'))
                self.port_var.set(str(config.get('PORT', 3306)))
                self.user_var.set(config.get('USER', 'root'))
                self.password_var.set(config.get('PASSWORD', ''))
                self.db_name_var.set(config.get('DB_NAME', 'helensystem_data'))
                self.backup_dir_var.set(config.get('BACKUP_DIR', r'C:\ruta\de\backup'))
                self.interval_hours.set(config.get('interval_hours', '24'))
                self.interval_minutes.set(config.get('interval_minutes', '0'))
                
                self.add_log("✓ Configuración cargada desde backup_config.json")
        except Exception as e:
            self.add_log(f"✗ Error al cargar configuración: {str(e)}")
    
    def add_log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # También imprimir en consola
        print(log_entry.strip())
    
    def clear_logs(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.add_log("Logs limpiados")
    
    def check_log_queue(self):
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.add_log(message)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.check_log_queue)
    
    def validate_interval(self):
        try:
            hours = int(self.interval_hours.get())
            minutes = int(self.interval_minutes.get())
            if hours < 0 or minutes < 0 or minutes >= 60:
                raise ValueError
            if hours == 0 and minutes == 0:
                raise ValueError("El intervalo debe ser mayor a 0")
            return hours, minutes
        except ValueError:
            messagebox.showerror("Error", "Por favor ingresa un intervalo válido (horas >= 0, minutos 0-59)")
            return None, None
    
    def start_automatic_backup(self):
        hours, minutes = self.validate_interval()
        if hours is None:
            return
        
        config = self.get_db_config()
        if not all([config['HOST'], config['USER'], config['DB_NAME'], config['BACKUP_DIR']]):
            messagebox.showerror("Error", "Por favor complete todos los campos obligatorios")
            return
        
        if not os.path.exists(config['BACKUP_DIR']):
            try:
                os.makedirs(config['BACKUP_DIR'], exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear la carpeta: {e}")
                return
        
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.manual_button.config(state=tk.DISABLED)
        
        interval_seconds = (hours * 3600) + (minutes * 60)
        self.add_log(f"Iniciando backup automático cada {hours}h {minutes}m")
        
        # Iniciar hilo de backup
        self.backup_thread = threading.Thread(target=self.backup_worker, args=(interval_seconds,))
        self.backup_thread.daemon = True
        self.backup_thread.start()
    
    def stop_automatic_backup(self):
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.manual_button.config(state=tk.NORMAL)
        self.add_log("Deteniendo backup automático...")
    
    def manual_backup(self):
        config = self.get_db_config()
        if not all([config['HOST'], config['USER'], config['DB_NAME'], config['BACKUP_DIR']]):
            messagebox.showerror("Error", "Por favor complete todos los campos obligatorios")
            return
        
        self.add_log("Iniciando backup manual...")
        threading.Thread(target=self.perform_backup, daemon=True).start()
    
    def backup_worker(self, interval_seconds):
        # Realizar primer backup inmediatamente
        self.log_queue.put("Ejecutando primer backup...")
        self.perform_backup()
        
        while self.is_running:
            # Esperar el intervalo, pero verificar cada segundo si debemos parar
            for _ in range(interval_seconds):
                if not self.is_running:
                    break
                time.sleep(1)
            
            if self.is_running:
                self.log_queue.put("Ejecutando backup programado...")
                self.perform_backup()
        
        self.log_queue.put("Backup automático detenido")
    
    def perform_backup(self):
        try:
            config = self.get_db_config()
            
            # Redirigir la salida para capturar los mensajes del módulo principal
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            
            class LogCapture:
                def __init__(self, queue_ref):
                    self.queue = queue_ref
                
                def write(self, text):
                    if text.strip():
                        self.queue.put(text.strip())
                
                def flush(self):
                    pass
            
            log_capture = LogCapture(self.log_queue)
            sys.stdout = log_capture
            sys.stderr = log_capture
            
            try:
                # Ejecutar el backup con la configuración actual
                main.main(config)
                self.log_queue.put("✓ Backup completado exitosamente")
            except Exception as e:
                self.log_queue.put(f"✗ Error durante el backup: {str(e)}")
            finally:
                # Restaurar stdout y stderr
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                
        except Exception as e:
            self.log_queue.put(f"✗ Error crítico: {str(e)}")

def run_ui():
    root = tk.Tk()
    app = BackupUI(root)
    
    # Manejar el cierre de la ventana
    def on_closing():
        if app.is_running:
            if messagebox.askokcancel("Salir", "El backup automático está en ejecución. ¿Deseas detenerlo y salir?"):
                app.stop_automatic_backup()
                time.sleep(1)  # Dar tiempo para que se detenga
                root.destroy()
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    run_ui()