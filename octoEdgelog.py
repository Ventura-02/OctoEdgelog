import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os
import subprocess
import threading
import stat
import json
from tkinter import Button

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor de Pozos")
        self.selected_pozo_path = None
        self.processes = {}  # (tipo, pozo): subprocess.Popen
        self.logs = {}  # (tipo, pozo): log acumulado

        self.base_paths = {
            "01Enrichment": os.path.expanduser("~/Documents/01Enrichment"),
            "02RMSE": os.path.expanduser("~/Documents/02RMSE")
        }

        self.tipo_var = tk.StringVar(value="01Enrichment")
        self.root.configure(bg="#142b44")
        tipo_frame = tk.Frame(root, bg="#142b44", highlightthickness=0, bd=0, relief=tk.FLAT)
        tipo_frame.pack(pady=5)
        for tipo in self.base_paths:
            tk.Radiobutton(tipo_frame, text=tipo, variable=self.tipo_var, value=tipo, command=self.on_tipo_change,
                           font=("Arial", 11, "bold"), bg="#142b44", fg="#eff4fa", selectcolor="#715d82", activebackground="#142b44", bd=0, highlightthickness=0, relief=tk.FLAT).pack(side=tk.LEFT, padx=10)

        # Frame central para agrupar todo
        frame_central = tk.Frame(root, bg="#142b44")
        frame_central.pack(pady=5, padx=5, fill=tk.BOTH, expand=True)

        # Botones a la izquierda del listado de pozos (sin borde ni recuadro)
        frame_izq = tk.Frame(frame_central, bg="#142b44", bd=0, highlightthickness=0, relief=tk.FLAT)
        frame_izq.pack(side=tk.LEFT, padx=10, pady=10, anchor="n", fill=tk.Y)
        tk.Label(frame_izq, text="Acciones", font=("Arial", 12, "bold"), bg="#142b44", fg="#eff4fa").pack(pady=(0,10))
        tk.Button(frame_izq, text=" Editar config.yaml", command=self.editar_yaml, width=18, bg="#715d82", fg="#eff4fa", font=("Arial", 10, "bold"), activebackground="#715d82", activeforeground="#eff4fa", bd=0, highlightthickness=0, relief=tk.FLAT).pack(pady=4, fill=tk.X)

        tk.Button(frame_izq, text="▶️ Ejecutar Log", command=self.ejecutar_log, width=18, bg="#3cb371", fg="#eff4fa", font=("Arial", 10, "bold"), activebackground="#3cb371", activeforeground="#eff4fa", bd=0, highlightthickness=0, relief=tk.FLAT).pack(pady=4, fill=tk.X)
        tk.Button(frame_izq, text=" Dar permisos", command=self.dar_permisos_ejecucion, width=18, bg="#f4b942", fg="#142b44", font=("Arial", 10, "bold"), activebackground="#f4b942", activeforeground="#142b44", bd=0, highlightthickness=0, relief=tk.FLAT).pack(pady=4, fill=tk.X)
        frame_lista = tk.Frame(frame_central, bg="#142b44")
        frame_lista.pack(side=tk.LEFT, padx=40, pady=10, anchor="center", expand=True)
        

        tk.Label(frame_lista, text="Pozos", font=("Arial", 14, "bold"), bg="#142b44", fg="#eff4fa").pack(pady=(0,5))
        # Botón para refrescar la lista
        tk.Button(frame_lista, text="Recargar", command=self.actualizar_lista, bg="#142b44", fg="#FFD5B8", font=("Arial", 10, "bold"), activebackground="#142b44", activeforeground="#eff4fa", bd=0, highlightthickness=0, relief=tk.FLAT).pack(pady=(0, 10))


        # Subframe para lista y scrollbar
        sub_frame = tk.Frame(frame_lista, bg="#142b44")
        sub_frame.pack()

        # Scrollbar vertical
        scrollbar = tk.Scrollbar(sub_frame, orient=tk.VERTICAL)

        # Listbox con conexión a scrollbar
        self.lista_pozos = tk.Listbox(sub_frame, width=70, font=("Arial", 12), bg="#142b44", fg="#eff4fa",
                                    selectbackground="#715d82", selectforeground="#eff4fa",
                                    borderwidth=2, relief=tk.GROOVE,
                                    yscrollcommand=scrollbar.set,
                                    highlightbackground="#715d82", highlightcolor="#715d82")
        self.lista_pozos.pack(side=tk.LEFT, fill=tk.BOTH)

        scrollbar.config(command=self.lista_pozos.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Eventos
        self.lista_pozos.bind("<<ListboxSelect>>", self.seleccionar_pozo)
        self.lista_pozos.bind("<Delete>", self.eliminar_pozo_evento)


        # Botones a la derecha del listado de pozos (sin borde ni recuadro)
        frame_der = tk.Frame(frame_central, bg="#142b44", bd=0, highlightthickness=0, relief=tk.FLAT)
        frame_der.pack(side=tk.LEFT, padx=10, pady=5, anchor="n", fill=tk.Y)
        tk.Label(frame_der, text="Gestión de pozos", font=("Arial", 12, "bold"), bg="#142b44", fg="#eff4fa").pack(pady=(0,10))
        tk.Button(frame_der, text=" Copiar pozo", command=self.copiar_pozo, width=18, bg="#715d82", fg="#eff4fa", font=("Arial", 10, "bold"), activebackground="#715d82", activeforeground="#eff4fa", bd=0, highlightthickness=0, relief=tk.FLAT).pack(pady=4, fill=tk.X)
        tk.Button(frame_der, text=" Renombrar pozo", command=self.renombrar_pozo, width=18, bg="#715d82", fg="#eff4fa", font=("Arial", 10, "bold"), activebackground="#715d82", activeforeground="#eff4fa", bd=0, highlightthickness=0, relief=tk.FLAT).pack(pady=4, fill=tk.X)
        tk.Button(frame_der, text="️ Eliminar pozo", command=self.eliminar_pozo, width=18, bg="#e74c3c", fg="#eff4fa", font=("Arial", 10, "bold"), activebackground="#e74c3c", activeforeground="#eff4fa", bd=0, highlightthickness=0, relief=tk.FLAT).pack(pady=4, fill=tk.X)


     # Contenedor general que contiene la parte izquierda y derecha
        frame_contenedor = tk.Frame(root, bg="#142b44")
        frame_contenedor.pack(fill="both", expand=True, padx=10, pady=10)

        # --------------------------
        # Ventana izquierda: procesos activos
        procesos_frame = tk.Frame(frame_contenedor, bg="#142b44")
        procesos_frame.pack(side='left', fill="both", expand=True, padx=(0, 5))

        tk.Label(procesos_frame, text="Procesos Activos", font=("Arial", 12, "bold"), bg="#142b44", fg="#eff4fa").pack(pady=(0, 5))

        tk.Button(procesos_frame, text="⏹️ Detener proceso seleccionado", command=self.detener_proceso, bg="#e67e22", fg="#eff4fa", font=("Arial", 10, "bold"), activebackground="#e67e22", activeforeground="#eff4fa", bd=0, highlightthickness=0, relief=tk.FLAT).pack(pady=5)

        self.lista_procesos = tk.Listbox(procesos_frame, width=70, height=25, font=("Consolas", 10), bg="#142b44", fg="#eff4fa", selectbackground="#715d82", selectforeground="#eff4fa", borderwidth=2, relief=tk.GROOVE, highlightbackground="#715d82", highlightcolor="#715d82")
        self.lista_procesos.pack(side="top", fill="both", expand=True)
        self.lista_procesos.bind("<<ListboxSelect>>", self.mostrar_log_proceso)
        self.lista_procesos.bind("<Delete>", self.detener_proceso)

        # --------------------------
        # Ventana derecha: log
        self.log_text = scrolledtext.ScrolledText(frame_contenedor, height=25, width=80, font=("Consolas", 10), bg="#142b44", fg="#eff4fa", insertbackground="#eff4fa", borderwidth=2, relief=tk.GROOVE, highlightbackground="#715d82", highlightcolor="#715d82")
        self.log_text.pack(side='left', fill="both", expand=True, padx=(5, 0))


        # --- Buscador de pozos ---
        self.busqueda_var = tk.StringVar()
        self.busqueda_var.trace_add("write", self.filtrar_lista_pozos)
        tk.Label(frame_lista, text="Buscar pozo:", font=("Arial", 10), bg="#142b44", fg="#eff4fa").pack()
        self.entry_busqueda = tk.Entry(frame_lista, textvariable=self.busqueda_var, font=("Arial", 11), width=40)
        self.entry_busqueda.pack(pady=(0, 10))

        self.todos_los_pozos = []  # Para guardar todos los pozos y filtrar

        self.actualizar_lista()

        # Bind para confirmar cierre
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def actualizar_lista(self):
        self.lista_pozos.delete(0, tk.END)
        base_path = self.base_paths[self.tipo_var.get()]
        self.todos_los_pozos = []
        if os.path.exists(base_path):
            for nombre in sorted(os.listdir(base_path)):
                pozo_path = os.path.join(base_path, nombre)
                if os.path.isdir(pozo_path):
                    self.todos_los_pozos.append(nombre)
        self.filtrar_lista_pozos()

    def filtrar_lista_pozos(self, *args):
        filtro = self.busqueda_var.get().lower()
        self.lista_pozos.delete(0, tk.END)
        for nombre in self.todos_los_pozos:
            if filtro in nombre.lower():
                self.lista_pozos.insert(tk.END, nombre)

    def seleccionar_pozo(self, event):
        seleccion = self.lista_pozos.curselection()
        if seleccion:
            nombre_pozo = self.lista_pozos.get(seleccion)
            self.selected_pozo_path = os.path.join(self.base_paths[self.tipo_var.get()], nombre_pozo)

    def editar_yaml(self):
        if not self.selected_pozo_path:
            messagebox.showwarning("Advertencia", "Selecciona un pozo.")
            return

        yaml_path = os.path.join(self.selected_pozo_path, "config.yaml")
        if not os.path.exists(yaml_path):
            messagebox.showerror("Error", "No se encontró el archivo config.yaml.")
            return

        editor = tk.Toplevel(self.root)
        editor.title("Editor de config.yaml")
        text_area = scrolledtext.ScrolledText(editor, width=80, height=25)

        text_area.pack()

        with open(yaml_path, "r") as f:
            text_area.insert(tk.END, f.read())

        def guardar():
            with open(yaml_path, "w") as f:
                f.write(text_area.get(1.0, tk.END))
            messagebox.showinfo("Guardado", "Archivo guardado correctamente.")
            editor.destroy()

        tk.Button(editor, text="Guardar", command=guardar).pack(pady=5)

    def ejecutar_log(self):
        if not self.selected_pozo_path:
            return
        threading.Thread(target=self.run).start()

    def run(self):
        script_path = os.path.join(self.selected_pozo_path, "LogDrillingCalculation_v1.6")
        if not os.path.exists(script_path):
            return
        tipo = self.tipo_var.get()
        nombre_pozo = os.path.basename(self.selected_pozo_path)
        key = (tipo, nombre_pozo)
        try:
            process = subprocess.Popen(["./LogDrillingCalculation_v1.6"],
                                    cwd=self.selected_pozo_path,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    text=True)
            self.processes[key] = process
            self.logs[key] = ""
            self.root.after(100, self.actualizar_lista_procesos)

            def leer_salida():
                for line in process.stdout:
                    self.logs[key] += line
                    current_selection = self.lista_procesos.curselection()
                    if current_selection:
                        seleccionado = self.lista_procesos.get(current_selection[0])
                        if nombre_pozo in seleccionado:
                            self.mostrar_log_proceso()
                process.wait()
                self.logs[key] += "\n>> Proceso finalizado.\n"
                self.processes.pop(key, None)
                self.root.after(100, self.actualizar_lista_procesos)

            threading.Thread(target=leer_salida, daemon=True).start()

        except Exception as e:
            self.logs[key] = f"Error al ejecutar: {e}\n"

            self.mostrar_log_proceso()

    def dar_permisos_ejecucion(self):
        if not self.selected_pozo_path:
            messagebox.showwarning("Advertencia", "Selecciona un pozo.")
            return

        script_path = os.path.join(self.selected_pozo_path, "LogDrillingCalculation_v1.6")
        if not os.path.exists(script_path):
            messagebox.showerror("Error", "No se encontró LogDrillingCalculation_v1.6.")
            return

        try:
            os.chmod(script_path, os.stat(script_path).st_mode | stat.S_IEXEC)
            messagebox.showinfo("Éxito", "Permiso de ejecución otorgado.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo dar permiso: {e}")

    def actualizar_lista_procesos(self):
        self.lista_procesos.delete(0, tk.END)
        tipo = self.tipo_var.get()
        # Ordena los pozos alfabéticamente antes de insertarlos
        procesos = [
            pozo for (tipo_proc, pozo), proceso in self.processes.items()
            if tipo_proc == tipo
        ]
        for pozo in sorted(procesos):
            self.lista_procesos.insert(tk.END, f"{pozo}")

    def mostrar_log_proceso(self, event=None):
        seleccion = self.lista_procesos.curselection()
        if not seleccion:
            return
        seleccionado = self.lista_procesos.get(seleccion[0])
        nombre_pozo = seleccionado.split(" - ")[0]
        tipo = self.tipo_var.get()
        log = self.logs.get((tipo, nombre_pozo), "")
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, log)
        self.log_text.see(tk.END)

    def detener_proceso(self, event=None):
        # Si el evento es de tipo teclado, evitar propagación
        if event is not None:
            # Evita que el evento se propague y se llame dos veces
            if hasattr(event, 'widget') and event.widget != self.lista_procesos:
                return "break"

        seleccion = self.lista_procesos.curselection()
        if not seleccion:
            return
        seleccionado = self.lista_procesos.get(seleccion[0])
        nombre_pozo = seleccionado.split(" - ")[0]
        tipo = self.tipo_var.get()
        confirmar = messagebox.askyesno(
            "Confirmar",
            f"¿Seguro que deseas detener el proceso del pozo '{nombre_pozo}'?"
        )
        if not confirmar:
            return

        key = (tipo, nombre_pozo)
        proceso = self.processes.get(key)
        if proceso and proceso.poll() is None:
            proceso.terminate()
            self.logs[key] += "\n>> Proceso detenido manualmente.\n"
            self.actualizar_lista_procesos()
            self.mostrar_log_proceso()
          

    def crear_pozo(self):
        base_path = self.base_paths[self.tipo_var.get()]
        nombre = self.pedir_nombre("Nuevo pozo")
        if not nombre:
            return
        nuevo_path = os.path.join(base_path, nombre)
        if not os.path.exists(nuevo_path):
            os.makedirs(nuevo_path)
            with open(os.path.join(nuevo_path, "config.yaml"), "w") as f:
                f.write("")
        self.actualizar_lista()

    def copiar_pozo(self):
        if not self.selected_pozo_path:
            return
        base_path = self.base_paths[self.tipo_var.get()]
        nombre = self.pedir_nombre("Copiar pozo como")
        if not nombre:
            return
        destino = os.path.join(base_path, nombre)
        if not os.path.exists(destino):
            import shutil
            shutil.copytree(self.selected_pozo_path, destino)
        self.actualizar_lista()

    def renombrar_pozo(self):
        if not self.selected_pozo_path:
            return
        base_path = self.base_paths[self.tipo_var.get()]
        nombre_actual = os.path.basename(self.selected_pozo_path)
        nombre_nuevo = self.pedir_nombre("Renombrar pozo", nombre_actual)
        if not nombre_nuevo or nombre_nuevo == nombre_actual:
            return
        destino = os.path.join(base_path, nombre_nuevo)
        if not os.path.exists(destino):
            os.rename(self.selected_pozo_path, destino)
        self.actualizar_lista()

    def eliminar_pozo(self):
        if not self.selected_pozo_path:
            return
        nombre = os.path.basename(self.selected_pozo_path)
        if not self.confirmar_eliminacion_pozo(nombre):
            return
        import shutil
        shutil.rmtree(self.selected_pozo_path)
        self.selected_pozo_path = None
        self.actualizar_lista()

    def eliminar_pozo_evento(self, event=None):
        if not self.selected_pozo_path:
            return
        nombre = os.path.basename(self.selected_pozo_path)
        if self.confirmar_eliminacion_pozo(nombre):
            import shutil
            shutil.rmtree(self.selected_pozo_path)
            self.selected_pozo_path = None
            self.actualizar_lista()

    def confirmar_eliminacion_pozo(self, nombre):
        top = tk.Toplevel(self.root)
        top.title("Confirmar eliminación")
        top.configure(bg="#142b44")
        tk.Label(top, text=f"Para eliminar el pozo '{nombre}', escribe DELETE en mayúsculas:", bg="#142b44", fg="#eff4fa", font=("Arial", 11)).pack(padx=20, pady=(20,10))
        entry = tk.Entry(top, font=("Arial", 12, "bold"))
        entry.pack(padx=20, pady=10)
        entry.focus_set()
        result = []
        def confirmar():
            if entry.get() == "DELETE":
                result.append(True)
                top.destroy()
            else:
                messagebox.showerror("Error", "Debes escribir DELETE en mayúsculas para confirmar.")
        tk.Button(top, text="Confirmar", command=confirmar, bg="#715d82", fg="#eff4fa", font=("Arial", 10, "bold"), activebackground="#715d82", activeforeground="#eff4fa", bd=0).pack(pady=(0,20))
        self.root.wait_window(top)
        return bool(result)

    def on_tipo_change(self):
        self.actualizar_lista()
        self.actualizar_lista_procesos()
        
    def on_close(self):
        if messagebox.askyesno("Confirmar salida", "¿Seguro que deseas cerrar la aplicación?"):
            self.root.destroy()

    def pedir_nombre(self, titulo, valor_inicial=""):
        top = tk.Toplevel(self.root)
        top.title(titulo)
        tk.Label(top, text="Nombre:").pack(side=tk.LEFT)
        entry = tk.Entry(top)
        entry.pack(side=tk.LEFT)
        entry.insert(0, valor_inicial)
        nombre = []
        def ok():
            nombre.append(entry.get())
            top.destroy()
        tk.Button(top, text="OK", command=ok).pack(side=tk.LEFT)
        self.root.wait_window(top)
        return nombre[0] if nombre else None

    def ordenar_procesos_alfabeticamente(self):
        # Obtén todos los elementos de la lista
        procesos = list(self.lista_procesos.get(0, "end"))

        # Ordénalos alfabéticamente
        procesos.sort()
        # Limpia la lista y vuelve a insertar los procesos ordenados
        self.lista_procesos.delete(0, "end")
        for proceso in procesos:
            self.lista_procesos.insert("end", proceso)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
