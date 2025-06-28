import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
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
        self.root.title("Myhelen Backup")
        self.root.geometry("1000x800")
        
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
        # Configurar el estilo
        style = ttk.Style()
        
        # Crear notebook para organizar en pestañas
        notebook = ttk.Notebook(self.root, bootstyle="dark")
        notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # ========== PESTAÑA PRINCIPAL ==========
        main_tab = ttk.Frame(notebook)
        notebook.add(main_tab, text="📊 Dashboard Principal")
        
        # Header con título y estado
        self.create_header(main_tab)
        
        # Panel de control rápido
        self.create_control_panel(main_tab)
        
        # Área de logs mejorada
        self.create_logs_area(main_tab)
        
        # ========== PESTAÑA CONFIGURACIÓN ==========
        config_tab = ttk.Frame(notebook)
        notebook.add(config_tab, text="⚙️ Configuración")
        
        self.create_config_tab(config_tab)
        
        # ========== PESTAÑA ESTADÍSTICAS ==========
        stats_tab = ttk.Frame(notebook)
        notebook.add(stats_tab, text="📈 Estadísticas")
        
        self.create_stats_tab(stats_tab)
        
        # Log inicial
        self.add_log("🚀 Sistema de backup inicializado", "SUCCESS")
    
    def create_header(self, parent):
        """Crear header principal con título y estado"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=X, padx=20, pady=(20, 10))
        
        # Título principal
        title_label = ttk.Label(
            header_frame, 
            text="🛡️ Helen System - Backup", 
            font=("Segoe UI", 20, "bold"),
            bootstyle="primary"
        )
        title_label.pack(side=LEFT)
        
        # Estado del sistema
        self.status_frame = ttk.Frame(header_frame)
        self.status_frame.pack(side=RIGHT)
        
        self.status_label = ttk.Label(
            self.status_frame,
            text="● Detenido",
            font=("Segoe UI", 12, "bold"),
            bootstyle="danger"
        )
        self.status_label.pack()
        
        # Separador
        ttk.Separator(parent, orient=HORIZONTAL).pack(fill=X, padx=20, pady=10)
    
    def create_control_panel(self, parent):
        """Crear panel de control principal"""
        control_frame = ttk.LabelFrame(
            parent, 
            text="🎮 Panel de Control",
            bootstyle="info",
            padding=20
        )
        control_frame.pack(fill=X, padx=20, pady=(0, 10))
        
        # Fila 1: Configuración de intervalo
        interval_frame = ttk.Frame(control_frame)
        interval_frame.pack(fill=X, pady=(0, 15))
        
        ttk.Label(
            interval_frame, 
            text="⏰ Intervalo de backup:",
            font=("Segoe UI", 11, "bold")
        ).pack(side=LEFT)
        
        # Entrada de horas
        ttk.Entry(
            interval_frame, 
            textvariable=self.interval_hours, 
            width=5,
            font=("Segoe UI", 10),
            bootstyle="primary"
        ).pack(side=LEFT, padx=(10, 5))
        
        ttk.Label(interval_frame, text="horas", font=("Segoe UI", 10)).pack(side=LEFT)
        
        # Entrada de minutos
        ttk.Entry(
            interval_frame, 
            textvariable=self.interval_minutes, 
            width=5,
            font=("Segoe UI", 10),
            bootstyle="primary"
        ).pack(side=LEFT, padx=(10, 5))
        
        ttk.Label(interval_frame, text="minutos", font=("Segoe UI", 10)).pack(side=LEFT)
        
        # Fila 2: Botones principales
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=X)
        
        self.start_button = ttk.Button(
            button_frame, 
            text="▶️ Iniciar Backup Automático",
            command=self.start_automatic_backup,
            bootstyle="success-outline",
            width=25
        )
        self.start_button.pack(side=LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(
            button_frame, 
            text="⏹️ Detener",
            command=self.stop_automatic_backup,
            bootstyle="danger-outline",
            state=DISABLED,
            width=15
        )
        self.stop_button.pack(side=LEFT, padx=5)
        
        self.manual_button = ttk.Button(
            button_frame, 
            text="🔧 Backup Manual",
            command=self.manual_backup,
            bootstyle="warning-outline",
            width=20
        )
        self.manual_button.pack(side=LEFT, padx=5)
        
        # Botón de limpiar logs a la derecha
        ttk.Button(
            button_frame,
            text="🗑️ Limpiar",
            command=self.clear_logs,
            bootstyle="secondary-outline",
            width=12
        ).pack(side=RIGHT)
    
    def create_logs_area(self, parent):
        """Crear área de logs mejorada"""
        logs_frame = ttk.LabelFrame(
            parent,
            text="📝 Registro de Actividad",
            bootstyle="secondary",
            padding=15
        )
        logs_frame.pack(fill=BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Frame para el text widget con scrollbar personalizada
        text_frame = ttk.Frame(logs_frame)
        text_frame.pack(fill=BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            text_frame,
            height=15,
            state=DISABLED,
            font=("Consolas", 10),
            bg="#2b2b2b",
            fg="#ffffff",
            insertbackground="#ffffff",
            selectbackground="#404040"
        )
        self.log_text.pack(fill=BOTH, expand=True)
        
        # Configurar tags para diferentes tipos de mensajes
        self.log_text.tag_configure("SUCCESS", foreground="#4CAF50", font=("Consolas", 10, "bold"))
        self.log_text.tag_configure("ERROR", foreground="#F44336", font=("Consolas", 10, "bold"))
        self.log_text.tag_configure("WARNING", foreground="#FF9800", font=("Consolas", 10, "bold"))
        self.log_text.tag_configure("INFO", foreground="#2196F3", font=("Consolas", 10, "bold"))
    
    def create_config_tab(self, parent):
        """Crear pestaña de configuración"""
        # Scroll frame para la configuración
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # ========== CONFIGURACIÓN DE BASE DE DATOS ==========
        db_frame = ttk.LabelFrame(
            scrollable_frame, 
            text="🗄️ Configuración de Base de Datos",
            bootstyle="primary",
            padding=20
        )
        db_frame.pack(fill=X, padx=20, pady=20)
        
        # Grid para organizar los campos
        fields = [
            ("🌐 Host:", self.host_var),
            ("🔌 Puerto:", self.port_var),
            ("👤 Usuario:", self.user_var),
            ("🔒 Contraseña:", self.password_var),
            ("💾 Base de Datos:", self.db_name_var)
        ]
        
        for i, (label_text, var) in enumerate(fields):
            row_frame = ttk.Frame(db_frame)
            row_frame.pack(fill=X, pady=8)
            
            ttk.Label(
                row_frame, 
                text=label_text,
                font=("Segoe UI", 10, "bold"),
                width=18
            ).pack(side=LEFT)
            
            if "Contraseña" in label_text:
                entry = ttk.Entry(
                    row_frame, 
                    textvariable=var, 
                    show="*",
                    width=35,
                    font=("Segoe UI", 10)
                )
            else:
                entry = ttk.Entry(
                    row_frame, 
                    textvariable=var,
                    width=35,
                    font=("Segoe UI", 10)
                )
            entry.pack(side=LEFT, padx=(10, 0))
        
        # Directorio de backup con botón
        dir_frame = ttk.Frame(db_frame)
        dir_frame.pack(fill=X, pady=8)
        
        ttk.Label(
            dir_frame,
            text="📁 Dir. Backup:",
            font=("Segoe UI", 10, "bold"),
            width=18
        ).pack(side=LEFT)
        
        ttk.Entry(
            dir_frame,
            textvariable=self.backup_dir_var,
            width=30,
            font=("Segoe UI", 10)
        ).pack(side=LEFT, padx=(10, 5))
        
        ttk.Button(
            dir_frame,
            text="📂",
            command=self.browse_backup_dir,
            bootstyle="info-outline",
            width=5
        ).pack(side=LEFT)
        
        # Botones de configuración
        config_btn_frame = ttk.Frame(db_frame)
        config_btn_frame.pack(fill=X, pady=(20, 0))
        
        ttk.Button(
            config_btn_frame,
            text="🔍 Probar Conexión",
            command=self.test_connection,
            bootstyle="info",
            width=20
        ).pack(side=LEFT, padx=(0, 10))
        
        ttk.Button(
            config_btn_frame,
            text="💾 Guardar Config",
            command=self.save_config,
            bootstyle="success",
            width=20
        ).pack(side=LEFT, padx=5)
        
        ttk.Button(
            config_btn_frame,
            text="📂 Cargar Config",
            command=self.load_config,
            bootstyle="warning",
            width=20
        ).pack(side=LEFT, padx=5)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_stats_tab(self, parent):
        """Crear pestaña de estadísticas"""
        stats_frame = ttk.Frame(parent)
        stats_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Cards de estadísticas
        cards_frame = ttk.Frame(stats_frame)
        cards_frame.pack(fill=X, pady=(0, 20))
        
        # Card 1: Último backup
        self.create_stat_card(
            cards_frame,
            "🕐 Último Backup",
            "No disponible",
            "primary"
        ).pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        
        # Card 2: Total de backups
        self.create_stat_card(
            cards_frame,
            "📊 Total Backups",
            "0",
            "success"
        ).pack(side=LEFT, fill=X, expand=True, padx=5)
        
        # Card 3: Estado del sistema
        self.create_stat_card(
            cards_frame,
            "⚡ Estado",
            "Detenido",
            "danger"
        ).pack(side=LEFT, fill=X, expand=True, padx=(10, 0))
        
        # Área de información adicional
        info_frame = ttk.LabelFrame(
            stats_frame,
            text="ℹ️ Información del Sistema",
            bootstyle="info",
            padding=20
        )
        info_frame.pack(fill=BOTH, expand=True)
        
        # Información del sistema
        info_text = f"""
🖥️ Sistema Operativo: {os.name}
📂 Directorio Actual: {os.getcwd()}
🐍 Versión Python: {sys.version.split()[0]}
⏰ Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        ttk.Label(
            info_frame,
            text=info_text.strip(),
            font=("Segoe UI", 10),
            justify=LEFT
        ).pack(anchor=W)
    
    def create_stat_card(self, parent, title, value, bootstyle):
        """Crear una card de estadística"""
        card = ttk.LabelFrame(
            parent,
            text=title,
            bootstyle=bootstyle,
            padding=15
        )
        
        value_label = ttk.Label(
            card,
            text=value,
            font=("Segoe UI", 16, "bold"),
            bootstyle=bootstyle
        )
        value_label.pack()
        
        return card
    
    def update_status(self, status, message):
        """Actualizar el estado visual del sistema"""
        if status == "running":
            self.status_label.config(
                text="● Ejecutando",
                bootstyle="success"
            )
        elif status == "stopped":
            self.status_label.config(
                text="● Detenido",
                bootstyle="danger"
            )
        elif status == "working":
            self.status_label.config(
                text="● Trabajando...",
                bootstyle="warning"
            )
    
    def browse_backup_dir(self):
        directory = filedialog.askdirectory(initialdir=self.backup_dir_var.get())
        if directory:
            self.backup_dir_var.set(directory)
            self.add_log(f"📁 Carpeta de destino cambiada a: {directory}", "INFO")
    
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
                    self.log_queue.put(("✅ Conexión exitosa a la base de datos", "SUCCESS"))
                    messagebox.showinfo("Éxito", "¡Conexión exitosa a la base de datos!")
                else:
                    error_msg = result.stderr.strip() if result.stderr else "Error desconocido"
                    self.log_queue.put((f"❌ Error de conexión: {error_msg}", "ERROR"))
                    messagebox.showerror("Error", f"Error de conexión:\n{error_msg}")
                    
            except subprocess.TimeoutExpired:
                self.log_queue.put(("⏰ Timeout en la conexión", "ERROR"))
                messagebox.showerror("Error", "Timeout: La conexión tardó demasiado")
            except Exception as e:
                self.log_queue.put((f"❌ Error al probar conexión: {str(e)}", "ERROR"))
                messagebox.showerror("Error", f"Error al probar conexión:\n{str(e)}")
        
        self.add_log("🔍 Probando conexión a la base de datos...", "INFO")
        threading.Thread(target=test_in_thread, daemon=True).start()
    
    def save_config(self):
        """Guardar configuración actual"""
        config = self.get_db_config()
        config['interval_hours'] = self.interval_hours.get()
        config['interval_minutes'] = self.interval_minutes.get()
        
        try:
            with open("backup_config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            self.add_log("💾 Configuración guardada en backup_config.json", "SUCCESS")
            messagebox.showinfo("Éxito", "Configuración guardada correctamente")
        except Exception as e:
            self.add_log(f"❌ Error al guardar configuración: {str(e)}", "ERROR")
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
                
                self.add_log("📂 Configuración cargada desde backup_config.json", "SUCCESS")
        except Exception as e:
            self.add_log(f"❌ Error al cargar configuración: {str(e)}", "ERROR")
    
    def add_log(self, message, log_type="INFO"):
        """Agregar mensaje al log con tipo específico"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Iconos según el tipo
        icons = {
            "SUCCESS": "✅",
            "ERROR": "❌", 
            "WARNING": "⚠️",
            "INFO": "ℹ️"
        }
        
        icon = icons.get(log_type, "ℹ️")
        log_entry = f"[{timestamp}] {icon} {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_entry, log_type)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # También imprimir en consola
        print(log_entry.strip())
    
    def clear_logs(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.add_log("🗑️ Logs limpiados", "INFO")
    
    def check_log_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if isinstance(item, tuple):
                    message, log_type = item
                    self.add_log(message, log_type)
                else:
                    self.add_log(item)
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
        self.start_button.config(state=DISABLED)
        self.stop_button.config(state=NORMAL)
        self.manual_button.config(state=DISABLED)
        
        self.update_status("running", "Sistema en ejecución")
        
        interval_seconds = (hours * 3600) + (minutes * 60)
        self.add_log(f"🚀 Iniciando backup automático cada {hours}h {minutes}m", "SUCCESS")
        
        # Iniciar hilo de backup
        self.backup_thread = threading.Thread(target=self.backup_worker, args=(interval_seconds,))
        self.backup_thread.daemon = True
        self.backup_thread.start()
    
    def stop_automatic_backup(self):
        self.is_running = False
        self.start_button.config(state=NORMAL)
        self.stop_button.config(state=DISABLED)
        self.manual_button.config(state=NORMAL)
        
        self.update_status("stopped", "Sistema detenido")
        self.add_log("⏹️ Deteniendo backup automático...", "WARNING")
    
    def manual_backup(self):
        config = self.get_db_config()
        if not all([config['HOST'], config['USER'], config['DB_NAME'], config['BACKUP_DIR']]):
            messagebox.showerror("Error", "Por favor complete todos los campos obligatorios")
            return
        
        self.add_log("🔧 Iniciando backup manual...", "INFO")
        self.update_status("working", "Ejecutando backup")
        threading.Thread(target=self.perform_backup, daemon=True).start()
    
    def backup_worker(self, interval_seconds):
        # Realizar primer backup inmediatamente
        self.log_queue.put(("🚀 Ejecutando primer backup...", "INFO"))
        self.perform_backup()
        
        while self.is_running:
            # Esperar el intervalo, pero verificar cada segundo si debemos parar
            for _ in range(interval_seconds):
                if not self.is_running:
                    break
                time.sleep(1)
            
            if self.is_running:
                self.log_queue.put(("⏰ Ejecutando backup programado...", "INFO"))
                self.perform_backup()
        
        self.log_queue.put(("⏹️ Backup automático detenido", "WARNING"))
    
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
                        self.queue.put((text.strip(), "INFO"))
                
                def flush(self):
                    pass
            
            log_capture = LogCapture(self.log_queue)
            sys.stdout = log_capture
            sys.stderr = log_capture
            
            try:
                # Ejecutar el backup con la configuración actual
                main.main(config)
                self.log_queue.put(("✅ Backup completado exitosamente", "SUCCESS"))
            except Exception as e:
                self.log_queue.put((f"❌ Error durante el backup: {str(e)}", "ERROR"))
            finally:
                # Restaurar stdout y stderr
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                
                # Actualizar estado si no está en modo automático
                if not self.is_running:
                    self.update_status("stopped", "Backup manual completado")
                
        except Exception as e:
            self.log_queue.put((f"🔥 Error crítico: {str(e)}", "ERROR"))

def run_ui():
    # Crear la aplicación con tema moderno
    root = ttk.Window(
        title="Myhelen Backup",
        themename="superhero",  # Tema oscuro moderno
        size=(1000, 800),
        resizable=(True, True)
    )
    
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