import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

MESES_ES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

CUOTA_BASE = 200   # Aportación fija mensual por departamento para fondo de mejoras


ARCHIVO_DATOS  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gastos.json")
ARCHIVO_PAGOS  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pagos.json")


class AdministracionApp:
    """Controlador principal: gestiona la ventana y la navegación entre pantallas."""

    TAMANIOS = {
        "MenuPrincipal":  "400x650",
        "RegistroGastos": "620x580",
        "VistaRegistros": "680x490",
        "RegistroPagos":  "600x580",
        "VistaPagos":     "680x490",
        "SaldosAFavor":    "560x420",
        "SaldosPendientes":"560x420",
        "GenerarReporte":  "500x380",
    }

    def __init__(self, root):
        self.root = root
        self.root.title("Administración del Edificio")
        self.root.resizable(False, False)

        container = tk.Frame(root)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for FrameClass in (MenuPrincipal, RegistroGastos, VistaRegistros,
                           RegistroPagos, VistaPagos,
                           SaldosAFavor, SaldosPendientes, GenerarReporte):
            frame = FrameClass(container, self)
            self.frames[FrameClass.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("MenuPrincipal")

    def show_frame(self, name):
        self.root.geometry(self.TAMANIOS[name])
        self.frames[name].tkraise()
        if name in ("VistaRegistros", "VistaPagos", "SaldosAFavor",
                    "SaldosPendientes", "GenerarReporte"):
            self.frames[name].cargar_datos()
        elif name == "RegistroPagos":
            self.frames[name].actualizar_cuota_sugerida()


# ---------------------------------------------------------------------------
# Pantalla: Menú principal
# ---------------------------------------------------------------------------

class MenuPrincipal(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#F5F5F5")
        self.controller = controller
        self._construir_ui()

    def _construir_ui(self):
        tk.Frame(self, bg="#F5F5F5", height=36).pack()

        tk.Label(
            self,
            text="Administración del Edificio",
            font=("Arial", 18, "bold"),
            bg="#F5F5F5",
            fg="#1A237E",
        ).pack(pady=(0, 6))

        tk.Label(
            self,
            text="Selecciona una opción",
            font=("Arial", 11),
            bg="#F5F5F5",
            fg="#777777",
        ).pack(pady=(0, 28))

        tk.Button(
            self,
            text="Registro de Gastos",
            command=lambda: self.controller.show_frame("RegistroGastos"),
            font=("Arial", 12, "bold"),
            bg="#2E7D32",
            fg="white",
            activebackground="#1B5E20",
            activeforeground="white",
            width=26,
            height=2,
            cursor="hand2",
            relief="flat",
        ).pack(pady=8)

        tk.Button(
            self,
            text="Ver Registros de Gastos",
            command=lambda: self.controller.show_frame("VistaRegistros"),
            font=("Arial", 12, "bold"),
            bg="#1565C0",
            fg="white",
            activebackground="#0D47A1",
            activeforeground="white",
            width=26,
            height=2,
            cursor="hand2",
            relief="flat",
        ).pack(pady=8)

        tk.Button(
            self,
            text="Registro de Pagos",
            command=lambda: self.controller.show_frame("RegistroPagos"),
            font=("Arial", 12, "bold"),
            bg="#6A1B9A",
            fg="white",
            activebackground="#4A148C",
            activeforeground="white",
            width=26,
            height=2,
            cursor="hand2",
            relief="flat",
        ).pack(pady=8)

        tk.Button(
            self,
            text="Ver Pagos Guardados",
            command=lambda: self.controller.show_frame("VistaPagos"),
            font=("Arial", 12, "bold"),
            bg="#00695C",
            fg="white",
            activebackground="#004D40",
            activeforeground="white",
            width=26,
            height=2,
            cursor="hand2",
            relief="flat",
        ).pack(pady=8)

        tk.Button(
            self,
            text="Saldos a Favor",
            command=lambda: self.controller.show_frame("SaldosAFavor"),
            font=("Arial", 12, "bold"),
            bg="#2E7D32",
            fg="white",
            activebackground="#1B5E20",
            activeforeground="white",
            width=26,
            height=2,
            cursor="hand2",
            relief="flat",
        ).pack(pady=8)

        tk.Button(
            self,
            text="Saldos Pendientes",
            command=lambda: self.controller.show_frame("SaldosPendientes"),
            font=("Arial", 12, "bold"),
            bg="#B71C1C",
            fg="white",
            activebackground="#7F0000",
            activeforeground="white",
            width=26,
            height=2,
            cursor="hand2",
            relief="flat",
        ).pack(pady=8)

        tk.Button(
            self,
            text="Generar Reporte PDF",
            command=lambda: self.controller.show_frame("GenerarReporte"),
            font=("Arial", 12, "bold"),
            bg="#37474F",
            fg="white",
            activebackground="#263238",
            activeforeground="white",
            width=26,
            height=2,
            cursor="hand2",
            relief="flat",
        ).pack(pady=8)


# ---------------------------------------------------------------------------
# Pantalla: Registro de gastos
# ---------------------------------------------------------------------------

class RegistroGastos(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.gastos = [
            {"fecha": date.today().strftime("%d/%m/%Y"),
             "concepto": "Fondo de ahorro",
             "monto": CUOTA_BASE * 20}
        ]
        self._construir_ui()

    def _construir_ui(self):
        # --- Barra superior ---
        topbar = tk.Frame(self, pady=4)
        topbar.pack(fill="x", padx=8)
        tk.Button(
            topbar,
            text="← Volver",
            command=lambda: self.controller.show_frame("MenuPrincipal"),
            font=("Arial", 9),
            relief="flat",
            cursor="hand2",
            fg="#1565C0",
        ).pack(side="left")

        # --- Encabezado ---
        tk.Label(self, text="Registro de Gastos", font=("Arial", 16, "bold")).pack(
            pady=(4, 8)
        )

        # --- Formulario ---
        form = tk.Frame(self, padx=24, pady=8)
        form.pack(fill="x")

        CONCEPTOS = [
            "Artículos limpieza",
            "Servicio de basura",
            "Intendencia",
            "Portón",
            "Luz edificio b",
            "Fondo de mejoras",
            "Otros",
        ]

        tk.Label(form, text="Concepto:", font=("Arial", 11), width=10, anchor="w").grid(
            row=0, column=0, pady=6, sticky="w"
        )
        self.concepto_var = tk.StringVar()
        self.concepto_combo = ttk.Combobox(
            form,
            textvariable=self.concepto_var,
            values=CONCEPTOS,
            font=("Arial", 11),
            width=34,
            state="readonly",
        )
        self.concepto_combo.grid(row=0, column=1, padx=10, pady=6)
        self.concepto_combo.bind("<<ComboboxSelected>>", self._on_concepto_select)

        tk.Label(form, text="", width=10).grid(row=1, column=0)
        self.concepto_otro = tk.Entry(form, font=("Arial", 11), width=36, state="disabled")
        self.concepto_otro.grid(row=1, column=1, padx=10, pady=(0, 6))

        tk.Label(form, text="Fecha:", font=("Arial", 11), width=10, anchor="w").grid(
            row=2, column=0, pady=6, sticky="w"
        )
        self.fecha_entry, self.fecha_btn = self._crear_campo_fecha(form, 2)

        tk.Label(form, text="Monto ($):", font=("Arial", 11), width=10, anchor="w").grid(
            row=3, column=0, pady=6, sticky="w"
        )
        self.monto_entry = tk.Entry(form, font=("Arial", 11), width=36)
        self.monto_entry.grid(row=3, column=1, padx=10, pady=6)

        tk.Button(
            form,
            text="Agregar",
            command=self._agregar_gasto,
            font=("Arial", 11, "bold"),
            bg="#2E7D32",
            fg="white",
            activebackground="#1B5E20",
            activeforeground="white",
            width=12,
            cursor="hand2",
        ).grid(row=4, column=1, pady=10, sticky="e")

        # --- Separador ---
        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=20, pady=4)

        # --- Tabla ---
        tabla_frame = tk.Frame(self, padx=20)
        tabla_frame.pack(fill="both", expand=True)

        tk.Label(tabla_frame, text="Gastos del mes", font=("Arial", 11, "bold")).pack(
            anchor="w", pady=(6, 4)
        )

        cols = ("fecha", "concepto", "monto")
        self.tabla = ttk.Treeview(tabla_frame, columns=cols, show="headings", height=8)
        self.tabla.heading("fecha", text="Fecha")
        self.tabla.heading("concepto", text="Concepto")
        self.tabla.heading("monto", text="Monto")
        self.tabla.column("fecha", width=100, anchor="center")
        self.tabla.column("concepto", width=300, anchor="w")
        self.tabla.column("monto", width=140, anchor="e")
        self.tabla.pack(fill="both", expand=True)

        # --- Totales ---
        self.total_label = tk.Label(
            self, text="Total:  $0.00", font=("Arial", 12, "bold"), anchor="e"
        )
        self.total_label.pack(fill="x", padx=24, pady=(12, 2))

        self.cuota_label = tk.Label(
            self,
            text="Por departamento (÷20):  $0.00",
            font=("Arial", 11),
            anchor="e",
            fg="#555555",
        )
        self.cuota_label.pack(fill="x", padx=24, pady=(0, 6))

        tk.Button(
            self,
            text="Aceptar",
            command=self._guardar_registros,
            font=("Arial", 11, "bold"),
            bg="#1565C0",
            fg="white",
            activebackground="#0D47A1",
            activeforeground="white",
            width=14,
            cursor="hand2",
        ).pack(anchor="e", padx=24, pady=(0, 14))

        # Pre-cargar Fondo de ahorro en tabla
        for g in self.gastos:
            self.tabla.insert("", "end",
                              values=(g["fecha"], g["concepto"], f"${g['monto']:,.2f}"),
                              tags=("fondo",))
        self.tabla.tag_configure("fondo", foreground="#1565C0")
        total_init = sum(g["monto"] for g in self.gastos)
        self.total_label.config(text=f"Total:  ${total_init:,.2f}")
        self.cuota_label.config(text=f"Por departamento (÷20):  ${total_init / 20:,.2f}")

        self.concepto_combo.focus()

    def _crear_campo_fecha(self, parent, row):
        entry = tk.Entry(parent, font=("Arial", 11), width=28)
        entry.insert(0, date.today().strftime("%d/%m/%Y"))
        entry.config(state="readonly")
        entry.grid(row=row, column=1, padx=10, pady=6, sticky="w")

        def toggle():
            if str(entry.cget("state")) == "normal":
                entry.config(state="readonly")
                btn.config(text="Editar")
            else:
                entry.config(state="normal")
                btn.config(text="Bloquear")
                entry.focus()

        btn = tk.Button(
            parent, text="Editar", command=toggle, font=("Arial", 9), width=7, cursor="hand2"
        )
        btn.grid(row=row, column=2, padx=(0, 10), pady=6)
        return entry, btn

    def _resetear_campo_fecha(self, entry, btn):
        entry.config(state="normal")
        entry.delete(0, tk.END)
        entry.insert(0, date.today().strftime("%d/%m/%Y"))
        entry.config(state="readonly")
        btn.config(text="Editar")

    def _on_concepto_select(self, event=None):
        if self.concepto_var.get() == "Otros":
            self.concepto_otro.config(state="normal")
            self.concepto_otro.focus()
        else:
            self.concepto_otro.delete(0, tk.END)
            self.concepto_otro.config(state="disabled")

    def _agregar_gasto(self):
        seleccion = self.concepto_var.get()
        concepto = self.concepto_otro.get().strip() if seleccion == "Otros" else seleccion

        fecha = self.fecha_entry.get().strip()
        monto_str = self.monto_entry.get().strip()

        if not concepto:
            if seleccion == "Otros":
                messagebox.showerror("Campo requerido", "Escribe el concepto en el campo 'Otros'.")
                self.concepto_otro.focus()
            else:
                messagebox.showerror("Campo requerido", "Selecciona un concepto.")
                self.concepto_combo.focus()
            return

        try:
            monto = float(monto_str)
            if monto <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Monto inválido", "Ingresa un monto decimal positivo.\nEjemplo: 1500.50"
            )
            self.monto_entry.focus()
            return

        self.gastos.append({"fecha": fecha, "concepto": concepto, "monto": monto})
        self.tabla.insert("", "end", values=(fecha, concepto, f"${monto:,.2f}"))

        total = sum(g["monto"] for g in self.gastos)
        self.total_label.config(text=f"Total:  ${total:,.2f}")
        cuota = total / 20
        self.cuota_label.config(text=f"Por departamento (÷20):  ${cuota:,.2f}")

        self.concepto_var.set("")
        self.concepto_otro.delete(0, tk.END)
        self.concepto_otro.config(state="disabled")
        self._resetear_campo_fecha(self.fecha_entry, self.fecha_btn)
        self.monto_entry.delete(0, tk.END)
        self.concepto_combo.focus()

    def _guardar_registros(self):
        if not self.gastos:
            messagebox.showwarning("Sin datos", "No hay gastos para guardar.")
            return

        total = sum(g["monto"] for g in self.gastos)
        registro = {
            "guardado_en": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "gastos": list(self.gastos),
            "total": total,
            "cuota_por_depto": total / 20,
        }

        datos = []
        if os.path.exists(ARCHIVO_DATOS):
            with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
                datos = json.load(f)

        datos.append(registro)

        with open(ARCHIVO_DATOS, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)

        messagebox.showinfo(
            "Guardado",
            f"Registro guardado correctamente.\n"
            f"{len(self.gastos)} gasto(s)  —  Total: ${total:,.2f}",
        )


# ---------------------------------------------------------------------------
# Pantalla: Vista de registros guardados
# ---------------------------------------------------------------------------

class VistaRegistros(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._construir_ui()

    def _construir_ui(self):
        # --- Barra superior ---
        topbar = tk.Frame(self, pady=4)
        topbar.pack(fill="x", padx=8)
        tk.Button(
            topbar,
            text="← Volver",
            command=lambda: self.controller.show_frame("MenuPrincipal"),
            font=("Arial", 9),
            relief="flat",
            cursor="hand2",
            fg="#1565C0",
        ).pack(side="left")

        tk.Label(self, text="Registros guardados", font=("Arial", 13, "bold")).pack(
            pady=(4, 6)
        )

        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=16, pady=(0, 4))

        cols = ("guardado_en", "n_gastos", "total", "cuota")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings tree")
        self.tree.heading("#0", text="")
        self.tree.column("#0", width=20, stretch=False)
        self.tree.heading("guardado_en", text="Guardado en")
        self.tree.heading("n_gastos", text="Gastos")
        self.tree.heading("total", text="Total")
        self.tree.heading("cuota", text="Por depto")
        self.tree.column("guardado_en", width=160, anchor="center")
        self.tree.column("n_gastos", width=60, anchor="center")
        self.tree.column("total", width=130, anchor="e")
        self.tree.column("cuota", width=130, anchor="e")

        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.tree.tag_configure("sesion", background="#E3F2FD")

        # --- Botones de acción ---
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill="x", padx=16, pady=(6, 10))

        tk.Button(
            btn_frame,
            text="Editar gasto",
            command=self._editar_seleccionado,
            font=("Arial", 10, "bold"),
            bg="#E65100",
            fg="white",
            activebackground="#BF360C",
            activeforeground="white",
            width=14,
            cursor="hand2",
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame,
            text="Eliminar",
            command=self._eliminar_seleccionado,
            font=("Arial", 10, "bold"),
            bg="#C62828",
            fg="white",
            activebackground="#B71C1C",
            activeforeground="white",
            width=14,
            cursor="hand2",
        ).pack(side="left")

    # --- Helpers de persistencia ---

    def _leer_datos(self):
        if not os.path.exists(ARCHIVO_DATOS):
            return []
        with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
            return json.load(f)

    def _guardar_datos(self, datos):
        with open(ARCHIVO_DATOS, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)

    def _parsear_iid(self, iid):
        """Devuelve (session_idx, gas_idx) — gas_idx es None si es fila de sesión."""
        parts = iid.split("_")
        if len(parts) == 2:          # "ses_N"
            return int(parts[1]), None
        return int(parts[1]), int(parts[3])   # "ses_N_gas_M"

    # --- Carga de datos ---

    def cargar_datos(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        datos = self._leer_datos()

        for original_idx in range(len(datos) - 1, -1, -1):
            reg = datos[original_idx]
            self.tree.insert(
                "",
                "end",
                iid=f"ses_{original_idx}",
                text="",
                values=(
                    reg["guardado_en"],
                    len(reg["gastos"]),
                    f"${reg['total']:,.2f}",
                    f"${reg['cuota_por_depto']:,.2f}",
                ),
                tags=("sesion",),
            )
            for gas_idx, g in enumerate(reg["gastos"]):
                self.tree.insert(
                    f"ses_{original_idx}",
                    "end",
                    iid=f"ses_{original_idx}_gas_{gas_idx}",
                    values=(g["fecha"], "", f"${g['monto']:,.2f}", g["concepto"]),
                )

    # --- Acciones ---

    def _eliminar_seleccionado(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Nada seleccionado", "Selecciona un registro o un gasto para eliminar.")
            return

        session_idx, gas_idx = self._parsear_iid(seleccion[0])
        datos = self._leer_datos()

        if gas_idx is None:
            # Eliminar sesión completa
            reg = datos[session_idx]
            if not messagebox.askyesno(
                "Eliminar registro",
                f"¿Eliminar el registro del {reg['guardado_en']}?\n"
                f"Se eliminarán {len(reg['gastos'])} gasto(s).",
            ):
                return
            del datos[session_idx]
        else:
            # Eliminar gasto individual
            g = datos[session_idx]["gastos"][gas_idx]
            if g["concepto"] == "Fondo de ahorro":
                messagebox.showwarning(
                    "No permitido",
                    "El 'Fondo de ahorro' es un concepto fijo y no puede eliminarse."
                )
                return
            if not messagebox.askyesno(
                "Eliminar gasto",
                f"¿Eliminar '{g['concepto']}' (${g['monto']:,.2f})?",
            ):
                return
            del datos[session_idx]["gastos"][gas_idx]
            if not datos[session_idx]["gastos"]:
                # Sesión quedó vacía → eliminarla también
                del datos[session_idx]
            else:
                gastos_rest = datos[session_idx]["gastos"]
                nuevo_total = sum(g["monto"] for g in gastos_rest)
                datos[session_idx]["total"] = nuevo_total
                tiene_fondo = any(g["concepto"] == "Fondo de ahorro" for g in gastos_rest)
                datos[session_idx]["cuota_por_depto"] = (
                    nuevo_total / 20 if tiene_fondo else nuevo_total / 20 + CUOTA_BASE
                )

        self._guardar_datos(datos)
        self.cargar_datos()

    def _editar_seleccionado(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Nada seleccionado", "Selecciona un gasto individual para editar.")
            return

        session_idx, gas_idx = self._parsear_iid(seleccion[0])
        if gas_idx is None:
            messagebox.showinfo(
                "Selecciona un gasto",
                "Selecciona un gasto individual (fila interna) para editarlo.",
            )
            return

        datos = self._leer_datos()
        gasto = datos[session_idx]["gastos"][gas_idx]
        if gasto["concepto"] == "Fondo de ahorro":
            messagebox.showwarning(
                "No editable",
                "El 'Fondo de ahorro' es un concepto fijo y no puede editarse."
            )
            return
        self._abrir_dialogo_editar(session_idx, gas_idx, gasto)

    def _abrir_dialogo_editar(self, session_idx, gas_idx, gasto):
        dlg = tk.Toplevel(self)
        dlg.title("Editar gasto")
        dlg.geometry("360x210")
        dlg.resizable(False, False)
        dlg.grab_set()

        form = tk.Frame(dlg, padx=20, pady=16)
        form.pack(fill="both", expand=True)

        tk.Label(form, text="Fecha:", font=("Arial", 11), width=10, anchor="w").grid(
            row=0, column=0, pady=7, sticky="w"
        )
        fecha_var = tk.Entry(form, font=("Arial", 11), width=20)
        fecha_var.insert(0, gasto["fecha"])
        fecha_var.grid(row=0, column=1, pady=7, sticky="w")

        tk.Label(form, text="Concepto:", font=("Arial", 11), width=10, anchor="w").grid(
            row=1, column=0, pady=7, sticky="w"
        )
        concepto_var = tk.Entry(form, font=("Arial", 11), width=20)
        concepto_var.insert(0, gasto["concepto"])
        concepto_var.grid(row=1, column=1, pady=7, sticky="w")

        tk.Label(form, text="Monto ($):", font=("Arial", 11), width=10, anchor="w").grid(
            row=2, column=0, pady=7, sticky="w"
        )
        monto_var = tk.Entry(form, font=("Arial", 11), width=20)
        monto_var.insert(0, str(gasto["monto"]))
        monto_var.grid(row=2, column=1, pady=7, sticky="w")

        def guardar():
            nueva_fecha = fecha_var.get().strip()
            nuevo_concepto = concepto_var.get().strip()
            nuevo_monto_str = monto_var.get().strip()

            if not nueva_fecha or not nuevo_concepto:
                messagebox.showerror("Campo requerido", "Fecha y concepto son obligatorios.", parent=dlg)
                return
            try:
                nuevo_monto = float(nuevo_monto_str)
                if nuevo_monto <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Monto inválido", "Ingresa un monto decimal positivo.", parent=dlg)
                return

            datos = self._leer_datos()
            datos[session_idx]["gastos"][gas_idx] = {
                "fecha": nueva_fecha,
                "concepto": nuevo_concepto,
                "monto": nuevo_monto,
            }
            gastos_todos = datos[session_idx]["gastos"]
            nuevo_total = sum(g["monto"] for g in gastos_todos)
            datos[session_idx]["total"] = nuevo_total
            tiene_fondo = any(g["concepto"] == "Fondo de ahorro" for g in gastos_todos)
            datos[session_idx]["cuota_por_depto"] = (
                nuevo_total / 20 if tiene_fondo else nuevo_total / 20 + CUOTA_BASE
            )
            self._guardar_datos(datos)
            dlg.destroy()
            self.cargar_datos()

        btn_frame = tk.Frame(dlg)
        btn_frame.pack(fill="x", padx=20, pady=(0, 14))
        tk.Button(
            btn_frame, text="Guardar", command=guardar,
            font=("Arial", 10, "bold"), bg="#2E7D32", fg="white",
            activebackground="#1B5E20", width=10, cursor="hand2",
        ).pack(side="right", padx=(6, 0))
        tk.Button(
            btn_frame, text="Cancelar", command=dlg.destroy,
            font=("Arial", 10), width=10, cursor="hand2",
        ).pack(side="right")

        fecha_var.focus()


# ---------------------------------------------------------------------------
# Pantalla: Registro de pagos de departamentos
# ---------------------------------------------------------------------------

class RegistroPagos(tk.Frame):
    DEPARTAMENTOS = [f"Depto {i}" for i in range(17, 37)]

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.pagos = []
        self._construir_ui()

    def _construir_ui(self):
        # --- Barra superior ---
        topbar = tk.Frame(self, pady=4)
        topbar.pack(fill="x", padx=8)
        tk.Button(
            topbar, text="← Volver",
            command=lambda: self.controller.show_frame("MenuPrincipal"),
            font=("Arial", 9), relief="flat", cursor="hand2", fg="#1565C0",
        ).pack(side="left")

        tk.Label(self, text="Registro de Pagos", font=("Arial", 16, "bold")).pack(pady=(4, 6))

        # --- Cuota del período (solo lectura, tomada del último registro de gastos) ---
        self.cuota_valor = 0.0
        cuota_frame = tk.Frame(self, padx=24)
        cuota_frame.pack(fill="x", pady=(0, 4))
        tk.Label(cuota_frame, text="Cuota del período:", font=("Arial", 11)).pack(side="left")
        self.cuota_display = tk.Label(
            cuota_frame, text="—", font=("Arial", 11, "bold"), fg="#1A237E"
        )
        self.cuota_display.pack(side="left", padx=(8, 0))
        self.cuota_origen = tk.Label(
            cuota_frame, text="", font=("Arial", 9), fg="#777777"
        )
        self.cuota_origen.pack(side="left", padx=(8, 0))

        # --- Formulario ---
        form = tk.Frame(self, padx=24, pady=4)
        form.pack(fill="x")

        tk.Label(form, text="Departamento:", font=("Arial", 11), width=14, anchor="w").grid(
            row=0, column=0, pady=6, sticky="w"
        )
        self.depto_var = tk.StringVar()
        self.depto_combo = ttk.Combobox(
            form, textvariable=self.depto_var, values=self.DEPARTAMENTOS,
            font=("Arial", 11), width=20, state="readonly",
        )
        self.depto_combo.grid(row=0, column=1, padx=10, pady=6, sticky="w")

        tk.Label(form, text="Fecha:", font=("Arial", 11), width=14, anchor="w").grid(
            row=1, column=0, pady=6, sticky="w"
        )
        self.fecha_pago_entry, self.fecha_pago_btn = self._crear_campo_fecha(form, 1)

        tk.Label(form, text="Monto pagado ($):", font=("Arial", 11), width=14, anchor="w").grid(
            row=2, column=0, pady=6, sticky="w"
        )
        self.monto_pago_var = tk.StringVar()
        self.monto_pago_entry = tk.Entry(
            form, textvariable=self.monto_pago_var, font=("Arial", 11), width=22
        )
        self.monto_pago_entry.grid(row=2, column=1, padx=10, pady=6, sticky="w")
        self.monto_pago_var.trace_add("write", lambda *_: self._actualizar_saldo_label())

        self.saldo_label = tk.Label(form, text="", font=("Arial", 10, "italic"), anchor="w")
        self.saldo_label.grid(row=3, column=1, padx=10, sticky="w")

        tk.Button(
            form, text="Agregar", command=self._agregar_pago,
            font=("Arial", 11, "bold"), bg="#6A1B9A", fg="white",
            activebackground="#4A148C", activeforeground="white", width=12, cursor="hand2",
        ).grid(row=4, column=1, pady=10, sticky="e")

        # --- Separador ---
        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=20, pady=4)

        # --- Tabla ---
        tabla_frame = tk.Frame(self, padx=20)
        tabla_frame.pack(fill="both", expand=True)

        tk.Label(tabla_frame, text="Pagos del período", font=("Arial", 11, "bold")).pack(
            anchor="w", pady=(4, 4)
        )

        cols = ("fecha", "departamento", "monto_pagado", "saldo")
        self.tabla = ttk.Treeview(tabla_frame, columns=cols, show="headings", height=7)
        self.tabla.heading("fecha",        text="Fecha")
        self.tabla.heading("departamento", text="Departamento")
        self.tabla.heading("monto_pagado", text="Monto pagado")
        self.tabla.heading("saldo",        text="Saldo")
        self.tabla.column("fecha",         width=95,  anchor="center")
        self.tabla.column("departamento",  width=145, anchor="w")
        self.tabla.column("monto_pagado",  width=130, anchor="e")
        self.tabla.column("saldo",         width=130, anchor="e")
        self.tabla.tag_configure("afavor",    foreground="#2E7D32")
        self.tabla.tag_configure("pendiente", foreground="#C62828")
        self.tabla.pack(fill="both", expand=True)

        # --- Totales ---
        self.total_pago_label = tk.Label(
            self, text="Total recaudado:  $0.00", font=("Arial", 12, "bold"), anchor="e"
        )
        self.total_pago_label.pack(fill="x", padx=24, pady=(8, 2))

        self.resumen_label = tk.Label(
            self, text="A favor: 0   |   Pendientes: 0",
            font=("Arial", 10), anchor="e", fg="#555555",
        )
        self.resumen_label.pack(fill="x", padx=24, pady=(0, 4))

        tk.Button(
            self, text="Aceptar", command=self._guardar_pagos,
            font=("Arial", 11, "bold"), bg="#1565C0", fg="white",
            activebackground="#0D47A1", activeforeground="white", width=14, cursor="hand2",
        ).pack(anchor="e", padx=24, pady=(0, 12))

        self.depto_combo.focus()

    # --- Campo de fecha reutilizable ---

    def _crear_campo_fecha(self, parent, row):
        entry = tk.Entry(parent, font=("Arial", 11), width=18)
        entry.insert(0, date.today().strftime("%d/%m/%Y"))
        entry.config(state="readonly")
        entry.grid(row=row, column=1, padx=10, pady=6, sticky="w")

        def toggle():
            if str(entry.cget("state")) == "normal":
                entry.config(state="readonly")
                btn.config(text="Editar")
            else:
                entry.config(state="normal")
                btn.config(text="Bloquear")
                entry.focus()

        btn = tk.Button(
            parent, text="Editar", command=toggle, font=("Arial", 9), width=7, cursor="hand2"
        )
        btn.grid(row=row, column=2, padx=(0, 10), pady=6)
        return entry, btn

    def _resetear_campo_fecha(self, entry, btn):
        entry.config(state="normal")
        entry.delete(0, tk.END)
        entry.insert(0, date.today().strftime("%d/%m/%Y"))
        entry.config(state="readonly")
        btn.config(text="Editar")

    # --- Sugerencia de cuota ---

    def actualizar_cuota_sugerida(self):
        """Carga la cuota del último registro de gastos guardado (siempre refresca)."""
        if not os.path.exists(ARCHIVO_DATOS):
            self.cuota_valor = CUOTA_BASE
            self.cuota_display.config(text=f"${CUOTA_BASE:,.2f}", fg="#1A237E")
            self.cuota_origen.config(text="(solo cuota base, sin gastos registrados)")
            return
        with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
            datos = json.load(f)
        if not datos:
            self.cuota_valor = CUOTA_BASE
            self.cuota_display.config(text=f"${CUOTA_BASE:,.2f}", fg="#1A237E")
            self.cuota_origen.config(text="(solo cuota base, sin gastos registrados)")
            return
        ultimo = datos[-1]
        tiene_fondo = any(
            g["concepto"] == "Fondo de ahorro" for g in ultimo.get("gastos", [])
        )
        self.cuota_valor = (
            ultimo["cuota_por_depto"] if tiene_fondo
            else ultimo["cuota_por_depto"] + CUOTA_BASE
        )
        self.cuota_display.config(
            text=f"${self.cuota_valor:,.2f}", fg="#1A237E"
        )
        self.cuota_origen.config(text=f"(guardado el {ultimo['guardado_en']})")

    # --- Saldo dinámico ---

    def _actualizar_saldo_label(self):
        try:
            saldo = float(self.monto_pago_var.get()) - self.cuota_valor
            if saldo > 0:
                self.saldo_label.config(text=f"Saldo: +${saldo:,.2f}  (a favor)", fg="#2E7D32")
            elif saldo < 0:
                self.saldo_label.config(text=f"Saldo: -${abs(saldo):,.2f}  (pendiente)", fg="#C62828")
            else:
                self.saldo_label.config(text="Saldo: $0.00  (exacto)", fg="#555555")
        except ValueError:
            self.saldo_label.config(text="", fg="#555555")

    # --- Agregar pago ---

    def _agregar_pago(self):
        depto = self.depto_var.get()
        if not depto:
            messagebox.showerror("Campo requerido", "Selecciona un departamento.")
            self.depto_combo.focus()
            return

        if any(p["departamento"] == depto for p in self.pagos):
            messagebox.showwarning("Duplicado", f"{depto} ya fue registrado en esta sesión.")
            return

        if self.cuota_valor <= 0:
            messagebox.showerror("Sin cuota", "No hay un registro de gastos guardado del cual obtener la cuota.")
            return

        try:
            monto = float(self.monto_pago_var.get())
            if monto <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Monto inválido", "Ingresa un monto decimal positivo.")
            self.monto_pago_entry.focus()
            return

        fecha = self.fecha_pago_entry.get().strip()
        saldo = monto - self.cuota_valor
        self.pagos.append({"fecha": fecha, "departamento": depto, "monto_pagado": monto, "saldo": saldo})

        saldo_str = f"+${saldo:,.2f}" if saldo >= 0 else f"-${abs(saldo):,.2f}"
        tag = "afavor" if saldo > 0 else ("pendiente" if saldo < 0 else "")
        self.tabla.insert("", "end", values=(fecha, depto, f"${monto:,.2f}", saldo_str),
                          tags=(tag,) if tag else ())

        total = sum(p["monto_pagado"] for p in self.pagos)
        a_favor    = sum(1 for p in self.pagos if p["saldo"] > 0)
        pendientes = sum(1 for p in self.pagos if p["saldo"] < 0)
        self.total_pago_label.config(text=f"Total recaudado:  ${total:,.2f}")
        self.resumen_label.config(text=f"A favor: {a_favor}   |   Pendientes: {pendientes}")

        self.depto_var.set("")
        self._resetear_campo_fecha(self.fecha_pago_entry, self.fecha_pago_btn)
        self.monto_pago_var.set("")
        self.saldo_label.config(text="", fg="#555555")
        self.depto_combo.focus()

    # --- Guardar ---

    def _guardar_pagos(self):
        if not self.pagos:
            messagebox.showwarning("Sin datos", "No hay pagos para guardar.")
            return

        total = sum(p["monto_pagado"] for p in self.pagos)
        registro = {
            "guardado_en":    datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "cuota_periodo":  self.cuota_valor,
            "pagos":          list(self.pagos),
            "total_recaudado": total,
        }

        datos = []
        if os.path.exists(ARCHIVO_PAGOS):
            with open(ARCHIVO_PAGOS, "r", encoding="utf-8") as f:
                datos = json.load(f)
        datos.append(registro)
        with open(ARCHIVO_PAGOS, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)

        messagebox.showinfo(
            "Guardado",
            f"Pagos guardados correctamente.\n"
            f"{len(self.pagos)} departamento(s)  —  Total: ${total:,.2f}",
        )


# ---------------------------------------------------------------------------
# Pantalla: Vista de pagos guardados
# ---------------------------------------------------------------------------

class VistaPagos(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._construir_ui()

    def _construir_ui(self):
        # --- Barra superior ---
        topbar = tk.Frame(self, pady=4)
        topbar.pack(fill="x", padx=8)
        tk.Button(
            topbar, text="← Volver",
            command=lambda: self.controller.show_frame("MenuPrincipal"),
            font=("Arial", 9), relief="flat", cursor="hand2", fg="#1565C0",
        ).pack(side="left")

        tk.Label(self, text="Pagos guardados", font=("Arial", 13, "bold")).pack(pady=(4, 6))

        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=16, pady=(0, 4))

        cols = ("guardado_en", "cuota", "n_deptos", "total")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings tree")
        self.tree.heading("#0", text="")
        self.tree.column("#0", width=20, stretch=False)
        self.tree.heading("guardado_en", text="Guardado en")
        self.tree.heading("cuota",       text="Cuota")
        self.tree.heading("n_deptos",    text="Deptos")
        self.tree.heading("total",       text="Total recaudado")
        self.tree.column("guardado_en", width=155, anchor="center")
        self.tree.column("cuota",       width=95,  anchor="e")
        self.tree.column("n_deptos",    width=65,  anchor="center")
        self.tree.column("total",       width=150, anchor="e")

        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.tree.tag_configure("sesion",    background="#F3E5F5")
        self.tree.tag_configure("afavor",    foreground="#2E7D32")
        self.tree.tag_configure("pendiente", foreground="#C62828")

        # --- Botones ---
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill="x", padx=16, pady=(6, 10))

        tk.Button(
            btn_frame, text="Editar pago", command=self._editar_seleccionado,
            font=("Arial", 10, "bold"), bg="#E65100", fg="white",
            activebackground="#BF360C", width=14, cursor="hand2",
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame, text="Eliminar", command=self._eliminar_seleccionado,
            font=("Arial", 10, "bold"), bg="#C62828", fg="white",
            activebackground="#B71C1C", width=14, cursor="hand2",
        ).pack(side="left")

    # --- Persistencia ---

    def _leer_datos(self):
        if not os.path.exists(ARCHIVO_PAGOS):
            return []
        with open(ARCHIVO_PAGOS, "r", encoding="utf-8") as f:
            return json.load(f)

    def _guardar_datos(self, datos):
        with open(ARCHIVO_PAGOS, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)

    def _parsear_iid(self, iid):
        parts = iid.split("_")
        if len(parts) == 2:       # "pag_N"
            return int(parts[1]), None
        return int(parts[1]), int(parts[3])   # "pag_N_dep_M"

    # --- Carga ---

    def cargar_datos(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        datos = self._leer_datos()

        for original_idx in range(len(datos) - 1, -1, -1):
            reg = datos[original_idx]
            self.tree.insert(
                "", "end", iid=f"pag_{original_idx}", text="",
                values=(
                    reg["guardado_en"],
                    f"${reg['cuota_periodo']:,.2f}",
                    len(reg["pagos"]),
                    f"${reg['total_recaudado']:,.2f}",
                ),
                tags=("sesion",),
            )
            for dep_idx, p in enumerate(reg["pagos"]):
                saldo = p["saldo"]
                saldo_str = f"+${saldo:,.2f}" if saldo >= 0 else f"-${abs(saldo):,.2f}"
                tag = "afavor" if saldo > 0 else ("pendiente" if saldo < 0 else "")
                self.tree.insert(
                    f"pag_{original_idx}", "end",
                    iid=f"pag_{original_idx}_dep_{dep_idx}",
                    values=(p["departamento"], f"${p['monto_pagado']:,.2f}", saldo_str,
                            p.get("fecha", "")),
                    tags=(tag,) if tag else (),
                )

    # --- Acciones ---

    def _eliminar_seleccionado(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Nada seleccionado", "Selecciona un registro o pago para eliminar.")
            return

        session_idx, dep_idx = self._parsear_iid(seleccion[0])
        datos = self._leer_datos()

        if dep_idx is None:
            reg = datos[session_idx]
            if not messagebox.askyesno(
                "Eliminar registro",
                f"¿Eliminar el registro del {reg['guardado_en']}?\n"
                f"Se eliminarán {len(reg['pagos'])} pago(s).",
            ):
                return
            del datos[session_idx]
        else:
            p = datos[session_idx]["pagos"][dep_idx]
            if not messagebox.askyesno(
                "Eliminar pago",
                f"¿Eliminar el pago de '{p['departamento']}' (${p['monto_pagado']:,.2f})?",
            ):
                return
            del datos[session_idx]["pagos"][dep_idx]
            if not datos[session_idx]["pagos"]:
                del datos[session_idx]
            else:
                datos[session_idx]["total_recaudado"] = sum(
                    p["monto_pagado"] for p in datos[session_idx]["pagos"]
                )

        self._guardar_datos(datos)
        self.cargar_datos()

    def _editar_seleccionado(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Nada seleccionado", "Selecciona un pago individual para editar.")
            return

        session_idx, dep_idx = self._parsear_iid(seleccion[0])
        if dep_idx is None:
            messagebox.showinfo(
                "Selecciona un pago",
                "Selecciona un pago individual (fila interna) para editarlo.",
            )
            return

        datos = self._leer_datos()
        pago  = datos[session_idx]["pagos"][dep_idx]
        cuota = datos[session_idx]["cuota_periodo"]
        self._abrir_dialogo_editar(session_idx, dep_idx, pago, cuota)

    def _abrir_dialogo_editar(self, session_idx, dep_idx, pago, cuota):
        dlg = tk.Toplevel(self)
        dlg.title("Editar pago")
        dlg.geometry("360x250")
        dlg.resizable(False, False)
        dlg.grab_set()

        form = tk.Frame(dlg, padx=20, pady=16)
        form.pack(fill="both", expand=True)

        tk.Label(form, text="Departamento:", font=("Arial", 11), width=14, anchor="w").grid(
            row=0, column=0, pady=6, sticky="w"
        )
        depto_combo = ttk.Combobox(
            form, values=RegistroPagos.DEPARTAMENTOS,
            font=("Arial", 11), width=18, state="readonly",
        )
        depto_combo.set(pago["departamento"])
        depto_combo.grid(row=0, column=1, pady=6, sticky="w")

        tk.Label(form, text="Fecha:", font=("Arial", 11), width=14, anchor="w").grid(
            row=1, column=0, pady=6, sticky="w"
        )
        fecha_entry = tk.Entry(form, font=("Arial", 11), width=20)
        fecha_entry.insert(0, pago.get("fecha", date.today().strftime("%d/%m/%Y")))
        fecha_entry.grid(row=1, column=1, pady=6, sticky="w")

        tk.Label(form, text="Monto pagado ($):", font=("Arial", 11), width=14, anchor="w").grid(
            row=2, column=0, pady=6, sticky="w"
        )
        monto_entry = tk.Entry(form, font=("Arial", 11), width=20)
        monto_entry.insert(0, str(pago["monto_pagado"]))
        monto_entry.grid(row=2, column=1, pady=6, sticky="w")

        saldo_lbl = tk.Label(form, text="", font=("Arial", 10, "italic"), anchor="w")
        saldo_lbl.grid(row=3, column=1, sticky="w")

        def actualizar_saldo(*_):
            try:
                s = float(monto_entry.get()) - cuota
                if s > 0:
                    saldo_lbl.config(text=f"+${s:,.2f}  (a favor)", fg="#2E7D32")
                elif s < 0:
                    saldo_lbl.config(text=f"-${abs(s):,.2f}  (pendiente)", fg="#C62828")
                else:
                    saldo_lbl.config(text="$0.00  (exacto)", fg="#555555")
            except ValueError:
                saldo_lbl.config(text="")

        monto_entry.bind("<KeyRelease>", actualizar_saldo)
        actualizar_saldo()

        def guardar():
            nuevo_depto = depto_combo.get()
            nueva_fecha = fecha_entry.get().strip()
            if not nuevo_depto or not nueva_fecha:
                messagebox.showerror("Campo requerido", "Todos los campos son obligatorios.", parent=dlg)
                return
            try:
                nuevo_monto = float(monto_entry.get())
                if nuevo_monto <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Monto inválido", "Ingresa un monto decimal positivo.", parent=dlg)
                return

            datos = self._leer_datos()
            datos[session_idx]["pagos"][dep_idx] = {
                "fecha":         nueva_fecha,
                "departamento":  nuevo_depto,
                "monto_pagado":  nuevo_monto,
                "saldo":         nuevo_monto - cuota,
            }
            datos[session_idx]["total_recaudado"] = sum(
                p["monto_pagado"] for p in datos[session_idx]["pagos"]
            )
            self._guardar_datos(datos)
            dlg.destroy()
            self.cargar_datos()

        btn_frame = tk.Frame(dlg)
        btn_frame.pack(fill="x", padx=20, pady=(0, 14))
        tk.Button(
            btn_frame, text="Guardar", command=guardar,
            font=("Arial", 10, "bold"), bg="#2E7D32", fg="white",
            activebackground="#1B5E20", width=10, cursor="hand2",
        ).pack(side="right", padx=(6, 0))
        tk.Button(
            btn_frame, text="Cancelar", command=dlg.destroy,
            font=("Arial", 10), width=10, cursor="hand2",
        ).pack(side="right")

        monto_entry.focus()


# ---------------------------------------------------------------------------
# Pantallas: Resumen de saldos (base compartida)
# ---------------------------------------------------------------------------

class _BaseResumenSaldos(tk.Frame):
    TITULO = ""
    SOLO_POSITIVOS = True

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._construir_ui()

    def _construir_ui(self):
        topbar = tk.Frame(self, pady=4)
        topbar.pack(fill="x", padx=8)
        tk.Button(
            topbar, text="← Volver",
            command=lambda: self.controller.show_frame("MenuPrincipal"),
            font=("Arial", 9), relief="flat", cursor="hand2", fg="#1565C0",
        ).pack(side="left")

        tk.Label(self, text=self.TITULO, font=("Arial", 14, "bold")).pack(pady=(4, 8))

        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=16, pady=(0, 4))

        cols = ("departamento", "sesiones", "saldo_neto")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=10)
        self.tree.heading("departamento", text="Departamento")
        self.tree.heading("sesiones",     text="Sesiones")
        self.tree.heading("saldo_neto",   text="Saldo neto acumulado")
        self.tree.column("departamento", width=220, anchor="w")
        self.tree.column("sesiones",     width=80,  anchor="center")
        self.tree.column("saldo_neto",   width=200, anchor="e")

        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.resumen_label = tk.Label(
            self, text="", font=("Arial", 11, "bold"), anchor="e"
        )
        self.resumen_label.pack(fill="x", padx=24, pady=(8, 12))

    def cargar_datos(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not os.path.exists(ARCHIVO_PAGOS):
            self.resumen_label.config(text="Sin registros de pagos guardados.", fg="#777777")
            return

        with open(ARCHIVO_PAGOS, "r", encoding="utf-8") as f:
            datos = json.load(f)

        # Acumular saldos por departamento a través de todas las sesiones
        acumulado = {}
        for reg in datos:
            for p in reg["pagos"]:
                depto = p["departamento"]
                if depto not in acumulado:
                    acumulado[depto] = {"sesiones": 0, "saldo_neto": 0.0}
                acumulado[depto]["sesiones"] += 1
                acumulado[depto]["saldo_neto"] += p["saldo"]

        # Filtrar según el tipo de frame
        if self.SOLO_POSITIVOS:
            filtrados = {d: v for d, v in acumulado.items() if v["saldo_neto"] > 0}
            ordenados = sorted(filtrados.items(), key=lambda x: x[1]["saldo_neto"], reverse=True)
            tag, color = "afavor", "#2E7D32"
        else:
            filtrados = {d: v for d, v in acumulado.items() if v["saldo_neto"] < 0}
            ordenados = sorted(filtrados.items(), key=lambda x: x[1]["saldo_neto"])
            tag, color = "pendiente", "#C62828"

        self.tree.tag_configure(tag, foreground=color)

        for depto, vals in ordenados:
            s = vals["saldo_neto"]
            saldo_str = f"+${s:,.2f}" if s >= 0 else f"-${abs(s):,.2f}"
            self.tree.insert("", "end",
                             values=(depto, vals["sesiones"], saldo_str),
                             tags=(tag,))

        total = sum(v["saldo_neto"] for v in filtrados.values())
        n = len(filtrados)

        if n == 0:
            self.resumen_label.config(text="Sin departamentos en esta categoría.", fg="#777777")
        elif self.SOLO_POSITIVOS:
            self.resumen_label.config(
                text=f"{n} departamento(s)  —  Total a favor: +${total:,.2f}", fg="#2E7D32"
            )
        else:
            self.resumen_label.config(
                text=f"{n} departamento(s)  —  Total pendiente: -${abs(total):,.2f}", fg="#C62828"
            )


# ---------------------------------------------------------------------------
# Pantalla: Generar reporte PDF
# ---------------------------------------------------------------------------

class GenerarReporte(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._meses_disponibles = []   # list of (label, mes_key) tuples
        self._construir_ui()

    def _construir_ui(self):
        topbar = tk.Frame(self, pady=4)
        topbar.pack(fill="x", padx=8)
        tk.Button(
            topbar, text="← Volver",
            command=lambda: self.controller.show_frame("MenuPrincipal"),
            font=("Arial", 9), relief="flat", cursor="hand2", fg="#1565C0",
        ).pack(side="left")

        tk.Label(self, text="Generar Reporte PDF", font=("Arial", 16, "bold")).pack(pady=(4, 10))

        form = tk.Frame(self, padx=30)
        form.pack(fill="x")

        tk.Label(form, text="Mes del reporte:", font=("Arial", 11), anchor="w").grid(
            row=0, column=0, sticky="w", pady=8
        )
        self.mes_var = tk.StringVar()
        self.mes_combo = ttk.Combobox(
            form, textvariable=self.mes_var, font=("Arial", 11),
            width=22, state="readonly",
        )
        self.mes_combo.grid(row=0, column=1, padx=12, pady=8, sticky="w")
        self.mes_combo.bind("<<ComboboxSelected>>", self._on_mes_select)

        # Info del mes seleccionado
        self.info_gastos = tk.Label(
            self, text="", font=("Arial", 10), fg="#444444", anchor="w", justify="left"
        )
        self.info_gastos.pack(fill="x", padx=30, pady=(4, 2))

        self.info_pagos = tk.Label(
            self, text="", font=("Arial", 10), fg="#444444", anchor="w", justify="left"
        )
        self.info_pagos.pack(fill="x", padx=30, pady=(0, 10))

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=20, pady=8)

        tk.Button(
            self, text="Generar PDF",
            command=self._generar_pdf,
            font=("Arial", 12, "bold"),
            bg="#37474F", fg="white",
            activebackground="#263238", activeforeground="white",
            width=18, height=2, cursor="hand2",
        ).pack(pady=10)

        self.estado_label = tk.Label(self, text="", font=("Arial", 10), fg="#2E7D32")
        self.estado_label.pack(pady=(0, 8))

    def cargar_datos(self):
        """Refresca la lista de meses disponibles desde gastos.json."""
        self.estado_label.config(text="")
        self.info_gastos.config(text="")
        self.info_pagos.config(text="")

        meses = {}   # mes_key -> label  e.g. "04/2026" -> "Abril 2026"

        if os.path.exists(ARCHIVO_DATOS):
            with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
                for reg in json.load(f):
                    mk = reg["guardado_en"][3:10]   # "MM/YYYY"
                    if mk not in meses:
                        mes_n = int(mk[:2])
                        meses[mk] = f"{MESES_ES[mes_n]} {mk[3:]}"

        self._meses_disponibles = sorted(meses.items(), reverse=True)
        labels = [lbl for _, lbl in self._meses_disponibles]
        self.mes_combo["values"] = labels

        if labels:
            self.mes_combo.current(0)
            self._on_mes_select()
        else:
            self.mes_combo.set("")
            self.info_gastos.config(text="No hay registros de gastos guardados.")

    def _on_mes_select(self, event=None):
        lbl = self.mes_var.get()
        mk = next((k for k, v in self._meses_disponibles if v == lbl), None)
        if not mk:
            return

        n_gastos, n_pagos, n_deptos = 0, 0, 0

        if os.path.exists(ARCHIVO_DATOS):
            with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
                for reg in json.load(f):
                    if reg["guardado_en"][3:10] == mk:
                        n_gastos += len(reg["gastos"])

        if os.path.exists(ARCHIVO_PAGOS):
            with open(ARCHIVO_PAGOS, "r", encoding="utf-8") as f:
                for reg in json.load(f):
                    if reg["guardado_en"][3:10] == mk:
                        n_pagos += 1
                        n_deptos += len(reg["pagos"])

        self.info_gastos.config(
            text=f"  Gastos registrados: {n_gastos} concepto(s)"
        )
        self.info_pagos.config(
            text=f"  Pagos registrados: {n_deptos} departamento(s) en {n_pagos} sesión(es)"
        )

    # ------------------------------------------------------------------

    def _generar_pdf(self):
        if not REPORTLAB_OK:
            messagebox.showerror(
                "Librería no disponible",
                "reportlab no está instalado.\n\n"
                "Ejecuta en la terminal:\n"
                "  sudo apt-get install python3-pip\n"
                "  python3 -m pip install reportlab",
            )
            return

        lbl = self.mes_var.get()
        mk = next((k for k, v in self._meses_disponibles if v == lbl), None)
        if not mk:
            messagebox.showwarning("Sin selección", "Selecciona un mes para generar el reporte.")
            return

        # Recolectar datos del mes
        gastos_mes, pagos_mes = [], []

        if os.path.exists(ARCHIVO_DATOS):
            with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
                for reg in json.load(f):
                    if reg["guardado_en"][3:10] == mk:
                        gastos_mes.append(reg)

        if os.path.exists(ARCHIVO_PAGOS):
            with open(ARCHIVO_PAGOS, "r", encoding="utf-8") as f:
                for reg in json.load(f):
                    if reg["guardado_en"][3:10] == mk:
                        pagos_mes.append(reg)

        if not gastos_mes and not pagos_mes:
            messagebox.showwarning("Sin datos", f"No hay datos para {lbl}.")
            return

        carpeta_reportes = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reportes")
        os.makedirs(carpeta_reportes, exist_ok=True)
        archivo = os.path.join(carpeta_reportes, f"reporte_{mk.replace('/', '_')}.pdf")
        _construir_pdf(archivo, lbl, gastos_mes, pagos_mes)
        self.estado_label.config(text=f"PDF generado: {os.path.basename(archivo)}")
        messagebox.showinfo(
            "PDF generado",
            f"Reporte guardado en:\n{archivo}",
        )
        import subprocess, sys
        if sys.platform.startswith("linux"):
            subprocess.Popen(["xdg-open", archivo])


def _construir_pdf(ruta, mes_label, gastos_mes, pagos_mes):
    """Genera el PDF de reporte mensual con reportlab."""
    doc = SimpleDocTemplate(
        ruta, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    estilos = getSampleStyleSheet()
    est_titulo = ParagraphStyle("titulo", parent=estilos["Title"],
                                fontSize=18, spaceAfter=4)
    est_subtitulo = ParagraphStyle("sub", parent=estilos["Normal"],
                                   fontSize=12, spaceAfter=2, alignment=TA_CENTER)
    est_seccion = ParagraphStyle("seccion", parent=estilos["Normal"],
                                 fontSize=12, fontName="Helvetica-Bold",
                                 spaceBefore=14, spaceAfter=6)
    est_pie = ParagraphStyle("pie", parent=estilos["Normal"],
                              fontSize=9, textColor=colors.grey, alignment=TA_CENTER)

    GRIS_ENCABEZADO = colors.HexColor("#37474F")
    GRIS_CLARO      = colors.HexColor("#ECEFF1")
    AZUL_TOTAL      = colors.HexColor("#E3F2FD")

    contenido = []

    # ── Encabezado ──────────────────────────────────────────────────────
    contenido.append(Paragraph("Administración del Edificio", est_titulo))
    contenido.append(Paragraph(f"Reporte Mensual — {mes_label}", est_subtitulo))
    contenido.append(Paragraph(
        f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        est_pie,
    ))
    contenido.append(HRFlowable(width="100%", thickness=1,
                                color=GRIS_ENCABEZADO, spaceAfter=12))

    ancho_pagina = A4[0] - 4*cm   # ancho útil

    # ── Sección 1: Gastos del edificio ──────────────────────────────────
    contenido.append(Paragraph("Desglose de Gastos del Edificio", est_seccion))

    if gastos_mes:
        # Aplanar todos los gastos del mes (puede haber varias sesiones)
        todos_gastos = [g for reg in gastos_mes for g in reg["gastos"]]
        total_gastos = sum(g["monto"] for g in todos_gastos)
        cuota = gastos_mes[-1]["cuota_por_depto"]   # cuota de la última sesión

        datos_tabla = [["Fecha", "Concepto", "Monto"]]
        for g in todos_gastos:
            datos_tabla.append([g["fecha"], g["concepto"], f"${g['monto']:,.2f}"])
        datos_tabla.append(["", "TOTAL", f"${total_gastos:,.2f}"])
        datos_tabla.append(["", "Cuota por departamento (÷20 incl. Fondo de ahorro)", f"${cuota:,.2f}"])

        col_w = [2.5*cm, ancho_pagina - 2.5*cm - 3*cm, 3*cm]
        t = Table(datos_tabla, colWidths=col_w, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), GRIS_ENCABEZADO),
            ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, 0), 10),
            ("BACKGROUND",  (0, 1), (-1, -3), GRIS_CLARO),
            ("ROWBACKGROUNDS", (0, 1), (-1, -3), [colors.white, GRIS_CLARO]),
            ("BACKGROUND",  (0, -2), (-1, -1), AZUL_TOTAL),
            ("FONTNAME",    (1, -2), (2, -1), "Helvetica-Bold"),
            ("ALIGN",       (2, 0), (2, -1), "RIGHT"),
            ("ALIGN",       (0, 0), (0, -1), "CENTER"),
            ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#B0BEC5")),
            ("FONTSIZE",    (0, 1), (-1, -1), 9),
            ("TOPPADDING",  (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        contenido.append(t)
    else:
        contenido.append(Paragraph("Sin gastos registrados para este mes.", estilos["Normal"]))

    # ── Sección 2: Pagos de departamentos ───────────────────────────────
    contenido.append(Spacer(1, 0.4*cm))
    contenido.append(Paragraph("Pagos de Departamentos", est_seccion))

    if pagos_mes:
        todos_pagos = [p for reg in pagos_mes for p in reg["pagos"]]
        total_recaudado = sum(p["monto_pagado"] for p in todos_pagos)

        datos_tabla2 = [["Departamento", "Fecha de Pago", "Monto Pagado"]]
        for p in sorted(todos_pagos, key=lambda x: x["departamento"]):
            datos_tabla2.append([
                p["departamento"],
                p.get("fecha", "—"),
                f"${p['monto_pagado']:,.2f}",
            ])
        datos_tabla2.append(["", "TOTAL RECAUDADO", f"${total_recaudado:,.2f}"])

        col_w2 = [ancho_pagina * 0.40, ancho_pagina * 0.33, ancho_pagina * 0.27]
        t2 = Table(datos_tabla2, colWidths=col_w2, repeatRows=1)
        t2.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), GRIS_ENCABEZADO),
            ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, 0), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, GRIS_CLARO]),
            ("BACKGROUND",  (0, -1), (-1, -1), AZUL_TOTAL),
            ("FONTNAME",    (1, -1), (2, -1), "Helvetica-Bold"),
            ("ALIGN",       (1, 0), (1, -1), "CENTER"),
            ("ALIGN",       (2, 0), (2, -1), "RIGHT"),
            ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#B0BEC5")),
            ("FONTSIZE",    (0, 1), (-1, -1), 9),
            ("TOPPADDING",  (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        contenido.append(t2)
    else:
        contenido.append(Paragraph("Sin pagos registrados para este mes.", estilos["Normal"]))

    # ── Pie de página ───────────────────────────────────────────────────
    contenido.append(Spacer(1, 0.6*cm))
    contenido.append(HRFlowable(width="100%", thickness=0.5,
                                color=colors.HexColor("#B0BEC5")))
    contenido.append(Paragraph(
        "Documento generado por el sistema de Administración del Edificio",
        est_pie,
    ))

    doc.build(contenido)


class SaldosAFavor(_BaseResumenSaldos):
    TITULO = "Departamentos con Saldo a Favor"
    SOLO_POSITIVOS = True


class SaldosPendientes(_BaseResumenSaldos):
    TITULO = "Departamentos con Saldo Pendiente"
    SOLO_POSITIVOS = False


# ---------------------------------------------------------------------------
root = tk.Tk()
AdministracionApp(root)
root.mainloop()
