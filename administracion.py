import calendar as _cal
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


ARCHIVO_DATOS        = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gastos.json")
ARCHIVO_PAGOS        = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pagos.json")
ARCHIVO_NOTAS        = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notas.json")
ARCHIVO_SEGUIMIENTO  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seguimiento_gastos.json")


def _abrir_pdf(ruta):
    """Abre un PDF usando el visor predeterminado, compatible con WSL."""
    import subprocess, shutil
    try:
        # Copiar a C:\LinuxMiatech\ para que Windows pueda acceder sin restricciones UNC
        nombre = os.path.basename(ruta)
        destino_win = f"/mnt/c/LinuxMiatech/{nombre}"
        shutil.copy2(ruta, destino_win)
        subprocess.Popen(["powershell.exe", "-c",
                          f"Start-Process 'C:\\LinuxMiatech\\{nombre}'"])
    except Exception:
        try:
            subprocess.Popen(["xdg-open", ruta])
        except Exception:
            pass


def _mes_key(reg):
    """Devuelve 'MM/YYYY' del período al que pertenece el registro."""
    return reg.get("mes_periodo") or reg["guardado_en"][3:10]


class CalendarioPopup(tk.Toplevel):
    """Popup de calendario para seleccionar una fecha visualmente."""

    _MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
              "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    _DIAS  = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]

    def __init__(self, parent, entry):
        super().__init__(parent)
        self.entry = entry
        self.title("Seleccionar fecha")
        self.resizable(False, False)
        self.transient(parent)   # asociar con ventana padre

        try:
            d = datetime.strptime(entry.get().strip(), "%d/%m/%Y")
            self._año, self._mes = d.year, d.month
        except ValueError:
            hoy = date.today()
            self._año, self._mes = hoy.year, hoy.month

        self._construir()
        self.update_idletasks()  # calcular tamaño real antes de posicionar
        self._posicionar()
        self.lift()
        self.focus_force()
        self.after(50, self._activar_grab)

    def _activar_grab(self):
        """Intenta grab_set una vez que la ventana está visible; reintenta si falla (WSL)."""
        try:
            self.grab_set()
        except tk.TclError:
            self.after(50, self._activar_grab)

    def _posicionar(self):
        """Posiciona el popup junto al Entry que lo originó, ajustando si se sale de pantalla."""
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()

        ex = self.entry.winfo_rootx()
        ey = self.entry.winfo_rooty()
        eh = self.entry.winfo_height()

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        x = ex
        y = ey + eh + 2          # debajo del entry por defecto

        if x + w > sw:           # se pasa por la derecha
            x = sw - w - 4
        if x < 0:
            x = 4
        if y + h > sh:           # no cabe abajo → aparece arriba
            y = ey - h - 2
        if y < 0:
            y = 4

        self.geometry(f"+{x}+{y}")

    def _construir(self):
        # — Encabezado: mes anterior / título / mes siguiente —
        header = tk.Frame(self, pady=6, padx=8)
        header.pack(fill="x")
        tk.Button(header, text="◀", command=self._mes_anterior,
                  font=("Arial", 10), width=2, cursor="hand2", relief="flat").pack(side="left")
        self._titulo = tk.Label(header, font=("Arial", 11, "bold"), width=22)
        self._titulo.pack(side="left", expand=True)
        tk.Button(header, text="▶", command=self._mes_siguiente,
                  font=("Arial", 10), width=2, cursor="hand2", relief="flat").pack(side="right")

        # — Nombres de días de la semana —
        sem_frame = tk.Frame(self, padx=8)
        sem_frame.pack()
        for col, nombre in enumerate(self._DIAS):
            tk.Label(sem_frame, text=nombre, font=("Arial", 9, "bold"),
                     width=4, anchor="center", fg="#555555").grid(row=0, column=col, padx=1)

        # — Grid de días (se redibuja al cambiar de mes) —
        self._grid = tk.Frame(self, padx=8, pady=4)
        self._grid.pack()

        tk.Button(self, text="Cancelar", command=self.destroy,
                  font=("Arial", 9), cursor="hand2").pack(pady=(0, 8))

        self._dibujar_mes()

    def _dibujar_mes(self):
        for w in self._grid.winfo_children():
            w.destroy()

        self._titulo.config(text=f"{self._MESES[self._mes - 1]}   {self._año}")
        hoy = date.today()

        for fila, semana in enumerate(_cal.monthcalendar(self._año, self._mes)):
            for col, dia in enumerate(semana):
                if dia == 0:
                    tk.Label(self._grid, width=4, height=1).grid(row=fila, column=col, padx=1, pady=1)
                    continue
                es_hoy = (dia == hoy.day and self._mes == hoy.month and self._año == hoy.year)
                btn_kw = dict(
                    text=str(dia), width=4, height=1,
                    font=("Arial", 9, "bold" if es_hoy else "normal"),
                    fg="white" if es_hoy else "black",
                    activebackground="#1E88E5", activeforeground="white",
                )
                if es_hoy:
                    btn_kw["bg"] = "#1565C0"
                btn = tk.Button(self._grid, **btn_kw,
                    relief="flat", cursor="hand2",
                    command=lambda d=dia: self._seleccionar(d),
                )
                btn.grid(row=fila, column=col, padx=1, pady=1)

    def _mes_anterior(self):
        if self._mes == 1:
            self._mes, self._año = 12, self._año - 1
        else:
            self._mes -= 1
        self._dibujar_mes()

    def _mes_siguiente(self):
        if self._mes == 12:
            self._mes, self._año = 1, self._año + 1
        else:
            self._mes += 1
        self._dibujar_mes()

    def _seleccionar(self, dia):
        fecha_str = date(self._año, self._mes, dia).strftime("%d/%m/%Y")
        self.entry.config(state="normal")
        self.entry.delete(0, tk.END)
        self.entry.insert(0, fecha_str)
        self.destroy()


class AdministracionApp:
    """Controlador principal: gestiona la ventana y la navegación entre pantallas."""

    TAMANIOS = {
        "MenuPrincipal":       "400x900",
        "RegistroGastos":      "620x620",
        "VistaRegistros":      "680x490",
        "RegistroPagos":       "600x580",
        "VistaPagos":          "680x490",
        "SaldosAFavor":        "560x420",
        "SaldosPendientes":    "560x420",
        "GenerarReporte":      "500x380",
        "ReporteGastos":       "500x400",
        "Notas":               "560x520",
        "SinPagarMes":         "420x720",
        "SeguimientoGastos":   "640x600",
    }

    def __init__(self, root):
        self.root = root
        self.root.title("Administración del Edificio")
        self.root.resizable(False, False)

        hoy = date.today()
        self.mes_activo = (hoy.month, hoy.year)

        container = tk.Frame(root)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for FrameClass in (MenuPrincipal, RegistroGastos, VistaRegistros,
                           RegistroPagos, VistaPagos,
                           SaldosAFavor, SaldosPendientes, GenerarReporte,
                           ReporteGastos, Notas, SinPagarMes,
                           SeguimientoGastos):
            frame = FrameClass(container, self)
            self.frames[FrameClass.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("MenuPrincipal")

    def show_frame(self, name):
        geo = self.TAMANIOS[name]
        self.root.geometry(geo)
        self.root.update_idletasks()
        w, h = map(int, geo.split("x"))
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{geo}+{x}+{y}")
        self.frames[name].tkraise()
        if name in ("VistaRegistros", "VistaPagos", "SaldosAFavor",
                    "SaldosPendientes", "GenerarReporte", "ReporteGastos",
                    "Notas", "SinPagarMes", "SeguimientoGastos"):
            self.frames[name].cargar_datos()
        elif name == "RegistroPagos":
            self.frames[name].actualizar_cuota_sugerida()
        elif name == "RegistroGastos":
            self.frames[name].actualizar_periodo()
        elif name == "MenuPrincipal":
            self.frames["MenuPrincipal"]._actualizar_periodo_label()


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
        ).pack(pady=(0, 8))

        # --- Selector de período activo ---
        periodo_frame = tk.Frame(self, bg="#F5F5F5")
        periodo_frame.pack(pady=(0, 4))

        tk.Button(
            periodo_frame, text="◀", command=self._mes_anterior,
            font=("Arial", 13, "bold"), bg="#F5F5F5", fg="#1A237E",
            relief="flat", cursor="hand2", activebackground="#F5F5F5",
        ).pack(side="left")

        self._periodo_label = tk.Label(
            periodo_frame, text="",
            font=("Arial", 13, "bold"),
            bg="#E8EAF6", fg="#1A237E",
            width=18, padx=10, pady=5,
        )
        self._periodo_label.pack(side="left", padx=6)

        tk.Button(
            periodo_frame, text="▶", command=self._mes_siguiente,
            font=("Arial", 13, "bold"), bg="#F5F5F5", fg="#1A237E",
            relief="flat", cursor="hand2", activebackground="#F5F5F5",
        ).pack(side="left")

        tk.Label(
            self, text="Período de trabajo activo",
            font=("Arial", 8), bg="#F5F5F5", fg="#9E9E9E",
        ).pack(pady=(0, 12))

        self._actualizar_periodo_label()

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
            text="Reporte de Gastos PDF",
            command=lambda: self.controller.show_frame("ReporteGastos"),
            font=("Arial", 12, "bold"),
            bg="#E65100",
            fg="white",
            activebackground="#BF360C",
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

        tk.Button(
            self,
            text="Sin pagar este mes",
            command=lambda: self.controller.show_frame("SinPagarMes"),
            font=("Arial", 12, "bold"),
            bg="#E65100",
            fg="white",
            activebackground="#BF360C",
            activeforeground="white",
            width=26,
            height=2,
            cursor="hand2",
            relief="flat",
        ).pack(pady=8)

        tk.Button(
            self,
            text="Notas y recordatorios",
            command=lambda: self.controller.show_frame("Notas"),
            font=("Arial", 12, "bold"),
            bg="#4527A0",
            fg="white",
            activebackground="#311B92",
            activeforeground="white",
            width=26,
            height=2,
            cursor="hand2",
            relief="flat",
        ).pack(pady=8)

        tk.Button(
            self,
            text="Gastos del Mes — Seguimiento",
            command=lambda: self.controller.show_frame("SeguimientoGastos"),
            font=("Arial", 12, "bold"),
            bg="#00838F",
            fg="white",
            activebackground="#006064",
            activeforeground="white",
            width=26,
            height=2,
            cursor="hand2",
            relief="flat",
        ).pack(pady=8)

    def _actualizar_periodo_label(self):
        m, y = self.controller.mes_activo
        self._periodo_label.config(text=f"{MESES_ES[m]}  {y}")

    def _mes_anterior(self):
        m, y = self.controller.mes_activo
        self.controller.mes_activo = (12, y - 1) if m == 1 else (m - 1, y)
        self._actualizar_periodo_label()

    def _mes_siguiente(self):
        m, y = self.controller.mes_activo
        self.controller.mes_activo = (1, y + 1) if m == 12 else (m + 1, y)
        self._actualizar_periodo_label()


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
            pady=(4, 2)
        )
        self.periodo_label = tk.Label(self, text="—", font=("Arial", 10), fg="#1A237E")
        self.periodo_label.pack(pady=(0, 8))

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

        botones_frame = tk.Frame(self)
        botones_frame.pack(fill="x", padx=24, pady=(0, 14))
        tk.Button(
            botones_frame,
            text="Generar Reporte",
            command=self._generar_reporte_actual,
            font=("Arial", 11, "bold"),
            bg="#E65100",
            fg="white",
            activebackground="#BF360C",
            activeforeground="white",
            width=16,
            cursor="hand2",
        ).pack(side="left")
        tk.Button(
            botones_frame,
            text="Aceptar",
            command=self._guardar_registros,
            font=("Arial", 11, "bold"),
            bg="#1565C0",
            fg="white",
            activebackground="#0D47A1",
            activeforeground="white",
            width=14,
            cursor="hand2",
        ).pack(side="right")

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
        entry = tk.Entry(parent, font=("Arial", 11), width=14)
        entry.insert(0, date.today().strftime("%d/%m/%Y"))
        entry.grid(row=row, column=1, padx=10, pady=6, sticky="w")

        btn = tk.Button(
            parent, text="Cal", command=lambda: CalendarioPopup(self, entry),
            font=("Arial", 11), width=3, cursor="hand2", relief="flat",
        )
        btn.grid(row=row, column=2, padx=(0, 10), pady=6)
        return entry, btn

    def _resetear_campo_fecha(self, entry, btn):
        entry.delete(0, tk.END)
        entry.insert(0, date.today().strftime("%d/%m/%Y"))

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

    def _generar_reporte_actual(self):
        if not REPORTLAB_OK:
            messagebox.showerror(
                "Librería no disponible",
                "reportlab no está instalado.\n\n"
                "Ejecuta en la terminal:\n"
                "  python3 -m pip install reportlab",
            )
            return
        if len(self.gastos) == 0:
            messagebox.showwarning("Sin datos", "No hay gastos para reportar.")
            return

        m, y = self.controller.mes_activo
        mes_label = f"{MESES_ES[m]} {y}"

        def _generar():
            try:
                carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reportes")
                os.makedirs(carpeta, exist_ok=True)
                nombre = f"gastos_{m:02d}_{y}_{datetime.now().strftime('%H%M%S')}.pdf"
                ruta = os.path.join(carpeta, nombre)
                _construir_pdf_gastos(ruta, mes_label, self.gastos)
                messagebox.showinfo("PDF generado", f"Reporte guardado en:\n{ruta}")
                _abrir_pdf(ruta)
            except Exception as e:
                messagebox.showerror("Error al generar PDF", str(e))

        _abrir_preview_gastos(self, mes_label, self.gastos, _generar)

    def actualizar_periodo(self):
        m, y = self.controller.mes_activo
        self.periodo_label.config(text=f"Período: {MESES_ES[m]} {y}")

    def _guardar_registros(self):
        if not self.gastos:
            messagebox.showwarning("Sin datos", "No hay gastos para guardar.")
            return

        m, y = self.controller.mes_activo
        total = sum(g["monto"] for g in self.gastos)
        registro = {
            "guardado_en": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "mes_periodo": f"{m:02d}/{y}",
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

        tk.Label(self, text="Registro de Pagos", font=("Arial", 16, "bold")).pack(pady=(4, 2))
        self.periodo_label = tk.Label(self, text="—", font=("Arial", 10), fg="#1A237E")
        self.periodo_label.pack(pady=(0, 4))

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
        monto_row = tk.Frame(form)
        monto_row.grid(row=2, column=1, padx=10, pady=6, sticky="w")

        self.monto_pago_var = tk.StringVar()
        self.monto_pago_entry = tk.Entry(
            monto_row, textvariable=self.monto_pago_var, font=("Arial", 11), width=15,
            state="readonly",
        )
        self.monto_pago_entry.pack(side="left")
        self.monto_pago_var.trace_add("write", lambda *_: self._actualizar_saldo_label())

        self.monto_total_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            monto_row, text="Monto total", variable=self.monto_total_var,
            command=self._toggle_monto_pago, font=("Arial", 10),
        ).pack(side="left", padx=(8, 0))

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
        self.tabla.tag_configure("afavor",         foreground="#2E7D32")
        self.tabla.tag_configure("pendiente",       foreground="#C62828")
        self.tabla.tag_configure("saldo_aplicado",  foreground="#1565C0", font=("Arial", 9, "italic"))
        self.tabla.pack(fill="both", expand=True)

        # --- Botones de acción sobre la tabla ---
        acc_frame = tk.Frame(tabla_frame)
        acc_frame.pack(anchor="e", pady=(4, 0))
        tk.Button(
            acc_frame, text="Editar", command=self._editar_pago,
            font=("Arial", 10), width=8, cursor="hand2",
            bg="#E65100", fg="white", activebackground="#BF360C", activeforeground="white",
        ).pack(side="left", padx=(0, 6))
        tk.Button(
            acc_frame, text="Eliminar", command=self._eliminar_pago,
            font=("Arial", 10), width=8, cursor="hand2",
            bg="#C62828", fg="white", activebackground="#B71C1C", activeforeground="white",
        ).pack(side="left")

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

        btns_frame = tk.Frame(self)
        btns_frame.pack(fill="x", padx=24, pady=(0, 12))

        tk.Button(
            btns_frame, text="Limpiar", command=self._limpiar_pagos,
            font=("Arial", 11), bg="#757575", fg="white",
            activebackground="#616161", activeforeground="white", width=10, cursor="hand2",
        ).pack(side="left")

        tk.Button(
            btns_frame, text="Aceptar", command=self._guardar_pagos,
            font=("Arial", 11, "bold"), bg="#1565C0", fg="white",
            activebackground="#0D47A1", activeforeground="white", width=14, cursor="hand2",
        ).pack(side="right")

        self.depto_combo.focus()

    # --- Campo de fecha reutilizable ---

    def _crear_campo_fecha(self, parent, row):
        entry = tk.Entry(parent, font=("Arial", 11), width=14)
        entry.insert(0, date.today().strftime("%d/%m/%Y"))
        entry.grid(row=row, column=1, padx=10, pady=6, sticky="w")

        btn = tk.Button(
            parent, text="Cal", command=lambda: CalendarioPopup(self, entry),
            font=("Arial", 11), width=3, cursor="hand2", relief="flat",
        )
        btn.grid(row=row, column=2, padx=(0, 10), pady=6)
        return entry, btn

    def _resetear_campo_fecha(self, entry, btn):
        entry.delete(0, tk.END)
        entry.insert(0, date.today().strftime("%d/%m/%Y"))

    # --- Sugerencia de cuota ---

    def actualizar_cuota_sugerida(self):
        """Carga la cuota del último registro de gastos del período activo."""
        m, y = self.controller.mes_activo
        mes_key = f"{m:02d}/{y}"
        self.periodo_label.config(text=f"Período: {MESES_ES[m]} {y}")

        if not os.path.exists(ARCHIVO_DATOS):
            self.cuota_valor = CUOTA_BASE
            self.cuota_display.config(text=f"${CUOTA_BASE:,.2f}", fg="#1A237E")
            self.cuota_origen.config(text="(solo cuota base, sin gastos registrados)")
            self._sincronizar_monto_total()
            return
        with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
            datos = json.load(f)
        if not datos:
            self.cuota_valor = CUOTA_BASE
            self.cuota_display.config(text=f"${CUOTA_BASE:,.2f}", fg="#1A237E")
            self.cuota_origen.config(text="(solo cuota base, sin gastos registrados)")
            self._sincronizar_monto_total()
            return

        # Preferir el último registro del mes activo; si no hay, usar el más reciente
        datos_mes = [r for r in datos if _mes_key(r) == mes_key]
        if datos_mes:
            ultimo = datos_mes[-1]
            origen_nota = ""
        else:
            ultimo = datos[-1]
            origen_nota = f" ⚠ (sin gastos para {MESES_ES[m]} {y})"

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
        self.cuota_origen.config(text=f"(guardado el {ultimo['guardado_en']}){origen_nota}")
        self._sincronizar_monto_total()
        self._aplicar_saldos_a_favor()

    def _aplicar_saldos_a_favor(self):
        """Auto-registra departamentos cuyo saldo neto acumulado >= cuota del período."""
        if self.cuota_valor <= 0 or not os.path.exists(ARCHIVO_PAGOS):
            return

        m, y = self.controller.mes_activo

        with open(ARCHIVO_PAGOS, "r", encoding="utf-8") as f:
            datos = json.load(f)

        # Saldo neto acumulado por departamento (histórico completo)
        acumulado = {}
        ya_pagaron_mes = set()
        for reg in datos:
            for p in reg["pagos"]:
                d = p["departamento"]
                acumulado[d] = acumulado.get(d, 0.0) + p["saldo"]
                try:
                    fp = datetime.strptime(p.get("fecha", ""), "%d/%m/%Y")
                    if fp.month == m and fp.year == y:
                        ya_pagaron_mes.add(d)
                except ValueError:
                    pass

        ya_en_sesion = {p["departamento"] for p in self.pagos}
        hoy = date.today().strftime("%d/%m/%Y")

        for d in self.DEPARTAMENTOS:
            if d in ya_pagaron_mes or d in ya_en_sesion:
                continue
            saldo_neto = acumulado.get(d, 0.0)
            if saldo_neto >= self.cuota_valor:
                # El saldo cubre la cuota: se registra como pago desde balance
                # monto_pagado=0 descuenta exactamente cuota del saldo acumulado
                self.pagos.append({
                    "fecha": hoy,
                    "departamento": d,
                    "monto_pagado": 0.0,
                    "saldo": -self.cuota_valor,
                })
                remanente = saldo_neto - self.cuota_valor
                rem_str = f"+${remanente:,.2f}" if remanente >= 0 else f"-${abs(remanente):,.2f}"
                self.tabla.insert("", "end",
                                  values=(hoy, d, "De saldo a favor", rem_str),
                                  tags=("saldo_aplicado",))

        self._actualizar_totales()

    # --- Checkbox monto total ---

    def _toggle_monto_pago(self):
        if self.monto_total_var.get():
            self.monto_pago_entry.config(state="normal")
            self.monto_pago_var.set(f"{self.cuota_valor:.2f}")
            self.monto_pago_entry.config(state="readonly")
        else:
            self.monto_pago_entry.config(state="normal")
            self.monto_pago_var.set("")
            self.monto_pago_entry.focus()

    def _sincronizar_monto_total(self):
        """Si el checkbox está marcado, actualiza el entry con la cuota vigente."""
        if self.monto_total_var.get():
            self.monto_pago_entry.config(state="normal")
            self.monto_pago_var.set(f"{self.cuota_valor:.2f}")
            self.monto_pago_entry.config(state="readonly")

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

        self._actualizar_totales()

        self.depto_var.set("")
        self._resetear_campo_fecha(self.fecha_pago_entry, self.fecha_pago_btn)
        self.monto_pago_var.set("")
        self.saldo_label.config(text="", fg="#555555")
        self.depto_combo.focus()

    # --- Helpers de tabla ---

    def _actualizar_totales(self):
        total       = sum(p["monto_pagado"] for p in self.pagos)
        de_saldo    = sum(1 for p in self.pagos if p["monto_pagado"] == 0.0)
        a_favor     = sum(1 for p in self.pagos if p["saldo"] > 0)
        pendientes  = sum(1 for p in self.pagos if p["saldo"] < 0 and p["monto_pagado"] > 0)
        self.total_pago_label.config(text=f"Total recaudado:  ${total:,.2f}")
        extras = f"   |   De saldo: {de_saldo}" if de_saldo else ""
        self.resumen_label.config(text=f"A favor: {a_favor}   |   Pendientes: {pendientes}{extras}")

    def _eliminar_pago(self):
        sel = self.tabla.selection()
        if not sel:
            messagebox.showwarning("Nada seleccionado", "Selecciona un pago de la tabla para eliminar.")
            return
        iid = sel[0]
        idx = self.tabla.index(iid)
        depto = self.pagos[idx]["departamento"]
        if not messagebox.askyesno("Eliminar pago", f"¿Eliminar el pago de '{depto}'?"):
            return
        self.tabla.delete(iid)
        del self.pagos[idx]
        self._actualizar_totales()

    def _editar_pago(self):
        sel = self.tabla.selection()
        if not sel:
            messagebox.showwarning("Nada seleccionado", "Selecciona un pago de la tabla para editar.")
            return
        iid = sel[0]
        idx = self.tabla.index(iid)
        pago = self.pagos[idx]

        dlg = tk.Toplevel(self)
        dlg.title("Editar pago")
        dlg.geometry("400x270")
        dlg.resizable(False, False)
        dlg.wait_visibility()
        dlg.grab_set()

        form = tk.Frame(dlg, padx=20, pady=16)
        form.pack(fill="both", expand=True)

        tk.Label(form, text="Departamento:", font=("Arial", 11), width=14, anchor="w").grid(
            row=0, column=0, pady=6, sticky="w"
        )
        depto_combo = ttk.Combobox(
            form, values=self.DEPARTAMENTOS, font=("Arial", 11), width=18, state="readonly"
        )
        depto_combo.set(pago["departamento"])
        depto_combo.grid(row=0, column=1, pady=6, sticky="w")

        tk.Label(form, text="Fecha:", font=("Arial", 11), width=14, anchor="w").grid(
            row=1, column=0, pady=6, sticky="w"
        )
        fecha_entry = tk.Entry(form, font=("Arial", 11), width=14)
        fecha_entry.insert(0, pago.get("fecha", date.today().strftime("%d/%m/%Y")))
        fecha_entry.grid(row=1, column=1, pady=6, sticky="w")
        tk.Button(
            form, text="Cal", command=lambda: CalendarioPopup(dlg, fecha_entry),
            font=("Arial", 11), width=3, cursor="hand2", relief="flat",
        ).grid(row=1, column=2, padx=(4, 0), pady=6)

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
                s = float(monto_entry.get()) - self.cuota_valor
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
            nuevo_saldo = nuevo_monto - self.cuota_valor
            self.pagos[idx] = {
                "fecha": nueva_fecha, "departamento": nuevo_depto,
                "monto_pagado": nuevo_monto, "saldo": nuevo_saldo,
            }
            saldo_str = f"+${nuevo_saldo:,.2f}" if nuevo_saldo >= 0 else f"-${abs(nuevo_saldo):,.2f}"
            tag = "afavor" if nuevo_saldo > 0 else ("pendiente" if nuevo_saldo < 0 else "")
            self.tabla.item(iid, values=(nueva_fecha, nuevo_depto, f"${nuevo_monto:,.2f}", saldo_str),
                            tags=(tag,) if tag else ())
            self._actualizar_totales()
            dlg.destroy()

        btn_row = tk.Frame(form)
        btn_row.grid(row=4, column=0, columnspan=3, pady=(12, 0), sticky="e")
        tk.Button(btn_row, text="Guardar", command=guardar,
                  font=("Arial", 11, "bold"), bg="#1565C0", fg="white",
                  activebackground="#0D47A1", activeforeground="white", width=10, cursor="hand2",
                  ).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="Cancelar", command=dlg.destroy,
                  font=("Arial", 10), width=10, cursor="hand2",
                  ).pack(side="left")

    # --- Guardar ---

    def _limpiar_pagos(self):
        if not self.pagos:
            return
        if not messagebox.askyesno("Limpiar", "¿Limpiar todos los pagos de la tabla?"):
            return
        self.pagos.clear()
        self.tabla.delete(*self.tabla.get_children())
        self._actualizar_totales()

    def _guardar_pagos(self):
        if not self.pagos:
            messagebox.showwarning("Sin datos", "No hay pagos para guardar.")
            return

        m, y = self.controller.mes_activo
        total = sum(p["monto_pagado"] for p in self.pagos)
        registro = {
            "guardado_en":    datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "mes_periodo":    f"{m:02d}/{y}",
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

        # Limpiar sesión para evitar duplicados si se vuelve a presionar Aceptar
        self.pagos.clear()
        self.tabla.delete(*self.tabla.get_children())
        self._actualizar_totales()


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
        fecha_entry = tk.Entry(form, font=("Arial", 11), width=14)
        fecha_entry.insert(0, pago.get("fecha", date.today().strftime("%d/%m/%Y")))
        fecha_entry.grid(row=1, column=1, pady=6, sticky="w")
        tk.Button(
            form, text="Cal", command=lambda: CalendarioPopup(dlg, fecha_entry),
            font=("Arial", 11), width=3, cursor="hand2", relief="flat",
        ).grid(row=1, column=2, padx=(0, 10), pady=6)

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
            filtrados = {d: v for d, v in acumulado.items() if v["saldo_neto"] > 0.005}
            ordenados = sorted(filtrados.items(), key=lambda x: x[1]["saldo_neto"], reverse=True)
            tag, color = "afavor", "#2E7D32"
        else:
            filtrados = {d: v for d, v in acumulado.items() if v["saldo_neto"] < -0.005}
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
        """Refresca la lista de meses disponibles desde gastos.json y pagos.json."""
        self.estado_label.config(text="")
        self.info_gastos.config(text="")
        self.info_pagos.config(text="")

        meses = {}   # mes_key -> label  e.g. "04/2026" -> "Abril 2026"

        for archivo in (ARCHIVO_DATOS, ARCHIVO_PAGOS):
            if os.path.exists(archivo):
                with open(archivo, "r", encoding="utf-8") as f:
                    for reg in json.load(f):
                        mk = _mes_key(reg)
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
            self.info_gastos.config(text="No hay registros guardados.")

    def _on_mes_select(self, event=None):
        lbl = self.mes_var.get()
        mk = next((k for k, v in self._meses_disponibles if v == lbl), None)
        if not mk:
            return

        n_gastos, n_pagos, n_deptos = 0, 0, 0

        if os.path.exists(ARCHIVO_DATOS):
            with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
                for reg in json.load(f):
                    if _mes_key(reg) == mk:
                        n_gastos += len(reg["gastos"])

        if os.path.exists(ARCHIVO_PAGOS):
            with open(ARCHIVO_PAGOS, "r", encoding="utf-8") as f:
                for reg in json.load(f):
                    if _mes_key(reg) == mk:
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
                    if _mes_key(reg) == mk:
                        gastos_mes.append(reg)

        if os.path.exists(ARCHIVO_PAGOS):
            with open(ARCHIVO_PAGOS, "r", encoding="utf-8") as f:
                for reg in json.load(f):
                    if _mes_key(reg) == mk:
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
        _abrir_pdf(archivo)


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
# Vista previa de gastos (diálogo reutilizable)
# ---------------------------------------------------------------------------

def _abrir_preview_gastos(parent, mes_label, gastos_lista, on_confirmar):
    """Abre un Toplevel con la vista previa del reporte de gastos.
    on_confirmar() se llama si el usuario confirma la generación."""
    dlg = tk.Toplevel(parent)
    dlg.title(f"Vista previa — {mes_label}")
    dlg.geometry("580x490")
    dlg.resizable(False, False)
    dlg.grab_set()

    tk.Label(dlg, text="Vista previa del reporte",
             font=("Arial", 14, "bold")).pack(pady=(12, 2))
    tk.Label(dlg, text=mes_label,
             font=("Arial", 11), fg="#555555").pack(pady=(0, 8))

    tabla_frame = tk.Frame(dlg, padx=16)
    tabla_frame.pack(fill="both", expand=True)

    cols = ("fecha", "concepto", "monto")
    tree = ttk.Treeview(tabla_frame, columns=cols, show="headings", height=13)
    tree.heading("fecha",    text="Fecha")
    tree.heading("concepto", text="Concepto")
    tree.heading("monto",    text="Monto")
    tree.column("fecha",    width=90,  anchor="center")
    tree.column("concepto", width=320, anchor="w")
    tree.column("monto",    width=100, anchor="e")

    sb = ttk.Scrollbar(tabla_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    for g in gastos_lista:
        fondo = g["concepto"] == "Fondo de ahorro"
        tree.insert("", "end",
                    values=(g["fecha"], g["concepto"], f"${g['monto']:,.2f}"),
                    tags=("fondo",) if fondo else ())
    tree.tag_configure("fondo", foreground="#1565C0")

    total = sum(g["monto"] for g in gastos_lista)
    cuota = total / 20

    tk.Label(dlg, text=f"Total:  ${total:,.2f}",
             font=("Arial", 11, "bold"), anchor="e"
             ).pack(fill="x", padx=16, pady=(8, 2))
    tk.Label(dlg, text=f"Cuota por departamento (÷20):  ${cuota:,.2f}",
             font=("Arial", 10), anchor="e", fg="#555555"
             ).pack(fill="x", padx=16, pady=(0, 4))

    ttk.Separator(dlg, orient="horizontal").pack(fill="x", padx=16, pady=6)

    btn_frame = tk.Frame(dlg)
    btn_frame.pack(fill="x", padx=16, pady=(0, 12))

    tk.Button(btn_frame, text="Cancelar", command=dlg.destroy,
              font=("Arial", 10), width=12, cursor="hand2"
              ).pack(side="left")

    def _confirmar():
        dlg.destroy()
        on_confirmar()

    tk.Button(btn_frame, text="Generar PDF", command=_confirmar,
              font=("Arial", 11, "bold"), bg="#E65100", fg="white",
              activebackground="#BF360C", activeforeground="white",
              width=14, cursor="hand2"
              ).pack(side="right")


# ---------------------------------------------------------------------------
# Pantalla: Reporte de gastos PDF
# ---------------------------------------------------------------------------

class ReporteGastos(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._meses_disponibles = []
        self._construir_ui()

    def _construir_ui(self):
        topbar = tk.Frame(self, pady=4)
        topbar.pack(fill="x", padx=8)
        tk.Button(
            topbar, text="← Volver",
            command=lambda: self.controller.show_frame("MenuPrincipal"),
            font=("Arial", 9), relief="flat", cursor="hand2", fg="#1565C0",
        ).pack(side="left")

        tk.Label(self, text="Reporte de Gastos PDF", font=("Arial", 16, "bold")).pack(pady=(4, 10))

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

        self.info_label = tk.Label(
            self, text="", font=("Arial", 10), fg="#444444", anchor="w", justify="left"
        )
        self.info_label.pack(fill="x", padx=30, pady=(4, 10))

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=20, pady=8)

        tk.Button(
            self, text="Generar PDF",
            command=self._generar_pdf,
            font=("Arial", 12, "bold"),
            bg="#E65100", fg="white",
            activebackground="#BF360C", activeforeground="white",
            width=18, height=2, cursor="hand2",
        ).pack(pady=10)

        self.estado_label = tk.Label(self, text="", font=("Arial", 10), fg="#2E7D32")
        self.estado_label.pack(pady=(0, 8))

    def cargar_datos(self):
        self.estado_label.config(text="")
        self.info_label.config(text="")

        meses = {}
        if os.path.exists(ARCHIVO_DATOS):
            with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
                for reg in json.load(f):
                    mk = _mes_key(reg)
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
            self.info_label.config(text="No hay registros de gastos guardados.")

    def _on_mes_select(self, event=None):
        lbl = self.mes_var.get()
        mk = next((k for k, v in self._meses_disponibles if v == lbl), None)
        if not mk:
            return
        n = 0
        if os.path.exists(ARCHIVO_DATOS):
            with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
                for reg in json.load(f):
                    if _mes_key(reg) == mk:
                        n += len(reg["gastos"])
        self.info_label.config(text=f"  Gastos registrados: {n} concepto(s)")

    def _generar_pdf(self):
        if not REPORTLAB_OK:
            messagebox.showerror(
                "Librería no disponible",
                "reportlab no está instalado.\n\n"
                "Ejecuta en la terminal:\n"
                "  python3 -m pip install reportlab",
            )
            return

        lbl = self.mes_var.get()
        mk = next((k for k, v in self._meses_disponibles if v == lbl), None)
        if not mk:
            messagebox.showwarning("Sin selección", "Selecciona un mes para generar el reporte.")
            return

        gastos_lista = []
        if os.path.exists(ARCHIVO_DATOS):
            with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
                for reg in json.load(f):
                    if _mes_key(reg) == mk:
                        gastos_lista.extend(reg["gastos"])

        if not gastos_lista:
            messagebox.showwarning("Sin datos", f"No hay gastos registrados para {lbl}.")
            return

        def _generar():
            try:
                carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reportes")
                os.makedirs(carpeta, exist_ok=True)
                archivo = os.path.join(carpeta, f"gastos_{mk.replace('/', '_')}.pdf")
                _construir_pdf_gastos(archivo, lbl, gastos_lista)
                self.estado_label.config(text=f"PDF generado: {os.path.basename(archivo)}")
                messagebox.showinfo("PDF generado", f"Reporte guardado en:\n{archivo}")
                _abrir_pdf(archivo)
            except Exception as e:
                messagebox.showerror("Error al generar PDF", str(e))

        _abrir_preview_gastos(self, lbl, gastos_lista, _generar)


def _construir_pdf_gastos(ruta, mes_label, gastos_lista):
    """Genera PDF con el desglose de gastos del mes."""
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

    GRIS_ENCABEZADO = colors.HexColor("#E65100")
    GRIS_CLARO      = colors.HexColor("#FFF3E0")
    AZUL_TOTAL      = colors.HexColor("#FFE0B2")

    ancho_util = A4[0] - 4*cm

    contenido = []

    contenido.append(Paragraph("Administración del Edificio", est_titulo))
    contenido.append(Paragraph(f"Reporte de Gastos — {mes_label}", est_subtitulo))
    contenido.append(Paragraph(
        f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        est_pie,
    ))
    contenido.append(HRFlowable(width="100%", thickness=1,
                                color=GRIS_ENCABEZADO, spaceAfter=14))

    contenido.append(Paragraph("Desglose de Gastos del Edificio", est_seccion))

    total = sum(g["monto"] for g in gastos_lista)
    cuota = total / 20

    datos_tabla = [["Fecha", "Concepto", "Monto"]]
    for g in gastos_lista:
        datos_tabla.append([g["fecha"], g["concepto"], f"${g['monto']:,.2f}"])
    datos_tabla.append(["", "TOTAL", f"${total:,.2f}"])
    datos_tabla.append(["", "Cuota por departamento (÷20)", f"${cuota:,.2f}"])

    col_w = [2.5*cm, ancho_util - 2.5*cm - 3*cm, 3*cm]
    t = Table(datos_tabla, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  GRIS_ENCABEZADO),
        ("TEXTCOLOR",      (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",       (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, 0),  10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -3), [colors.white, GRIS_CLARO]),
        ("BACKGROUND",     (0, -2), (-1, -1), AZUL_TOTAL),
        ("FONTNAME",       (1, -2), (2, -1), "Helvetica-Bold"),
        ("ALIGN",          (2, 0), (2, -1),  "RIGHT"),
        ("ALIGN",          (0, 0), (0, -1),  "CENTER"),
        ("GRID",           (0, 0), (-1, -1), 0.4, colors.HexColor("#FFCCBC")),
        ("FONTSIZE",       (0, 1), (-1, -1), 9),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
    ]))
    contenido.append(t)

    doc.build(contenido)


# ---------------------------------------------------------------------------
# Pantalla: Notas
# ---------------------------------------------------------------------------

class Notas(tk.Frame):
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

        tk.Label(self, text="Notas y recordatorios", font=("Arial", 15, "bold")).pack(pady=(4, 8))

        # --- Entrada de nota ---
        entrada_frame = tk.Frame(self, padx=20)
        entrada_frame.pack(fill="x")
        tk.Label(entrada_frame, text="Nueva nota:", font=("Arial", 11), anchor="w").pack(anchor="w")
        self.texto_nota = tk.Text(entrada_frame, font=("Arial", 11), height=4, wrap="word",
                                  relief="solid", bd=1)
        self.texto_nota.pack(fill="x", pady=(4, 6))
        tk.Button(
            entrada_frame, text="Agregar nota", command=self._agregar_nota,
            font=("Arial", 11, "bold"), bg="#1565C0", fg="white",
            activebackground="#0D47A1", activeforeground="white", cursor="hand2", width=14,
        ).pack(anchor="e")

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=20, pady=10)

        # --- Lista de notas ---
        lista_frame = tk.Frame(self, padx=20)
        lista_frame.pack(fill="both", expand=True)
        tk.Label(lista_frame, text="Notas guardadas", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 4))

        cols = ("fecha", "nota")
        self.tree = ttk.Treeview(lista_frame, columns=cols, show="headings", height=8)
        self.tree.heading("fecha", text="Fecha")
        self.tree.heading("nota",  text="Nota")
        self.tree.column("fecha", width=130, anchor="center")
        self.tree.column("nota",  width=380, anchor="w")
        sb = ttk.Scrollbar(lista_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        tk.Button(
            self, text="Eliminar seleccionada", command=self._eliminar_nota,
            font=("Arial", 10), bg="#C62828", fg="white",
            activebackground="#B71C1C", activeforeground="white", cursor="hand2",
        ).pack(anchor="e", padx=20, pady=(8, 10))

        self._cargar_notas()

    def _leer_notas(self):
        if not os.path.exists(ARCHIVO_NOTAS):
            return []
        with open(ARCHIVO_NOTAS, "r", encoding="utf-8") as f:
            return json.load(f)

    def _guardar_notas(self, notas):
        with open(ARCHIVO_NOTAS, "w", encoding="utf-8") as f:
            json.dump(notas, f, ensure_ascii=False, indent=2)

    def _cargar_notas(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for n in self._leer_notas():
            self.tree.insert("", "end", values=(n["fecha"], n["texto"]))

    def _agregar_nota(self):
        texto = self.texto_nota.get("1.0", "end").strip()
        if not texto:
            messagebox.showwarning("Campo vacío", "Escribe una nota antes de agregar.")
            return
        notas = self._leer_notas()
        nueva = {"fecha": datetime.now().strftime("%d/%m/%Y %H:%M"), "texto": texto}
        notas.append(nueva)
        self._guardar_notas(notas)
        self.texto_nota.delete("1.0", "end")
        self._cargar_notas()

    def _eliminar_nota(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Nada seleccionado", "Selecciona una nota para eliminar.")
            return
        idx = self.tree.index(sel[0])
        notas = self._leer_notas()
        texto = notas[idx]["texto"][:60]
        if not messagebox.askyesno("Eliminar nota", f"¿Eliminar esta nota?\n\n«{texto}»"):
            return
        del notas[idx]
        self._guardar_notas(notas)
        self._cargar_notas()

    def cargar_datos(self):
        self._cargar_notas()


# ---------------------------------------------------------------------------
# Pantalla: Sin pagar este mes
# ---------------------------------------------------------------------------

class SinPagarMes(tk.Frame):
    """
    Muestra gráficamente qué departamentos no han pagado en la sesión más reciente.
    Cada piso tiene 4 deptos en las esquinas de un cuadrado, numerados en sentido
    horario desde la esquina superior-derecha:
      TL(+3) | TR(+0)
      BL(+2) | BR(+1)
    Pisos (de abajo hacia arriba):  Piso 1 = deptos 17-20, … Piso 5 = deptos 33-36.
    """

    # Clockwise desde TR: offset 0→TR, 1→BR, 2→BL, 3→TL
    _COLOR_PAGADO   = "#2E7D32"
    _COLOR_NOPAGADO = "#C62828"
    _COLOR_SIN_DATO = "#9E9E9E"
    _R    = 24    # radio del círculo
    _CW   = 360   # ancho del canvas por piso
    _CH   = 120   # alto del canvas por piso
    _PADX = 64    # margen horizontal al centro del círculo
    _PADY = 22    # margen vertical al centro del círculo

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
        tk.Button(
            topbar, text="↺ Actualizar",
            command=self.cargar_datos,
            font=("Arial", 9), relief="flat", cursor="hand2", fg="#555555",
        ).pack(side="right")

        self.titulo_label = tk.Label(self, text="Sin pagar este mes", font=("Arial", 15, "bold"))
        self.titulo_label.pack(pady=(4, 2))
        self.subtitulo = tk.Label(self, text="—", font=("Arial", 10), fg="#777777")
        self.subtitulo.pack(pady=(0, 6))

        # Leyenda
        leyenda = tk.Frame(self)
        leyenda.pack()
        for color, etiqueta in [(self._COLOR_PAGADO, "Pagado"),
                                 (self._COLOR_NOPAGADO, "Sin pagar"),
                                 (self._COLOR_SIN_DATO, "Sin registro")]:
            tk.Canvas(leyenda, width=14, height=14, bg=color,
                      highlightthickness=0).pack(side="left", padx=(8, 2))
            tk.Label(leyenda, text=etiqueta, font=("Arial", 9)).pack(side="left", padx=(0, 8))

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=20, pady=6)

        # Contenedor scrollable de pisos
        outer = tk.Frame(self)
        outer.pack(fill="both", expand=True, padx=20)
        canvas_scroll = tk.Canvas(outer, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas_scroll.yview)
        canvas_scroll.configure(yscrollcommand=sb.set)
        canvas_scroll.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._pisos_frame = tk.Frame(canvas_scroll)
        self._pisos_frame.bind(
            "<Configure>",
            lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all"))
        )
        canvas_scroll.create_window((0, 0), window=self._pisos_frame, anchor="nw")

        self.resumen_label = tk.Label(
            self, text="", font=("Arial", 11, "bold"), anchor="e"
        )
        self.resumen_label.pack(fill="x", padx=24, pady=(6, 10))

    def cargar_datos(self):
        for w in self._pisos_frame.winfo_children():
            w.destroy()

        m, y = self.controller.mes_activo
        self.titulo_label.config(text=f"Sin pagar — {MESES_ES[m]} {y}")

        pagados = set()
        sesion_label = "Sin sesiones guardadas"
        hay_datos = False

        if os.path.exists(ARCHIVO_PAGOS):
            with open(ARCHIVO_PAGOS, "r", encoding="utf-8") as f:
                datos = json.load(f)
            n_pagos = 0
            for reg in datos:
                for p in reg["pagos"]:
                    try:
                        fecha_pago = datetime.strptime(p.get("fecha", ""), "%d/%m/%Y")
                        if fecha_pago.month == m and fecha_pago.year == y:
                            pagados.add(p["departamento"])
                            n_pagos += 1
                            hay_datos = True
                    except ValueError:
                        pass
            if hay_datos:
                sesion_label = f"{n_pagos} pago(s) registrado(s) — {MESES_ES[m]} {y}"
            elif datos:
                sesion_label = f"Sin pagos con fecha de {MESES_ES[m]} {y}"

        self.subtitulo.config(text=sesion_label)

        todos = [f"Depto {i}" for i in range(17, 37)]
        sin_pagar = [d for d in todos if d not in pagados]

        # Dibujar pisos de mayor a menor (piso 5 arriba, piso 1 abajo)
        R, CW, CH = self._R, self._CW, self._CH
        PX, PY = self._PADX, self._PADY
        # Centros de cada círculo: clockwise desde TR
        # offset 0=TR, 1=BR, 2=BL, 3=TL
        esquinas = {
            0: (CW - PX, PY),       # TR
            1: (CW - PX, CH - PY),  # BR
            2: (PX,      CH - PY),  # BL
            3: (PX,      PY),       # TL
        }

        for piso in range(5, 0, -1):
            base = 17 + (piso - 1) * 4
            deptos_piso = [f"Depto {base + k}" for k in range(4)]

            piso_frame = tk.Frame(self._pisos_frame, bd=1, relief="groove", padx=6, pady=6)
            piso_frame.pack(fill="x", pady=4)

            cv = tk.Canvas(piso_frame, width=CW, height=CH, bg="#FAFAFA",
                           highlightthickness=0)
            cv.pack()

            # Rectángulo cuyos vértices coinciden con los centros de los círculos
            cv.create_rectangle(PX, PY, CW - PX, CH - PY,
                                outline="#CCCCCC", width=1)

            # Etiqueta del piso en el centro del rectángulo
            cv.create_text(CW // 2, CH // 2,
                           text=f"Piso {piso}", font=("Arial", 10, "bold"),
                           fill="#BBBBBB")

            # Puerta de referencia posicional (borde superior del rectángulo)
            door_x       = CW // 2   # x=180, centro horizontal
            dw           = 10        # semiancho: puerta de 20 px
            dy_body_top  = PY - 12   # y=10 — inicio del cuerpo rectangular
            door_fill    = "#BCAAA4"
            door_outline = "#4E342E"
            # Arco superior: semielipse con chord fill (y=0..10)
            cv.create_arc(
                door_x - dw, dy_body_top - dw,   # (170, 0)
                door_x + dw, dy_body_top + dw,   # (190, 20)
                start=0, extent=180, style="chord",
                fill=door_fill, outline=door_outline, width=1,
            )
            # Cuerpo rectangular de la puerta (y=10..22)
            cv.create_rectangle(
                door_x - dw, dy_body_top,   # (170, 10)
                door_x + dw, PY,             # (190, 22)
                fill=door_fill, outline=door_outline, width=1,
            )
            # Pomo (manija pequeña a la derecha)
            cv.create_oval(
                door_x + 4, PY - 7,   # (184, 15)
                door_x + 7, PY - 4,   # (187, 18)
                fill=door_outline, outline="",
            )

            for offset, (cx, cy) in esquinas.items():
                depto = deptos_piso[offset]
                if depto in pagados:
                    color = self._COLOR_PAGADO
                elif hay_datos:
                    color = self._COLOR_NOPAGADO
                else:
                    color = self._COLOR_SIN_DATO

                cv.create_oval(cx - R, cy - R, cx + R, cy + R,
                               fill=color, outline="white", width=2)
                cv.create_text(cx, cy, text=str(base + offset),
                               font=("Arial", 10, "bold"), fill="white")

        sin_pagar_count = len(sin_pagar)
        if hay_datos:
            self.resumen_label.config(
                text=f"{sin_pagar_count} de 20 sin pagar   |   {20 - sin_pagar_count} pagados",
                fg="#C62828" if sin_pagar_count else "#2E7D32"
            )
        else:
            self.resumen_label.config(text="Sin datos de pagos.", fg="#777777")


# ---------------------------------------------------------------------------
# Pantalla: Seguimiento de gastos del mes
# ---------------------------------------------------------------------------

class _EditarGastoDialog(tk.Toplevel):
    """Diálogo para editar un ítem de gasto en su lugar."""

    def __init__(self, parent, item, callback):
        super().__init__(parent)
        self._item     = item
        self._callback = callback
        self.title("Editar gasto")
        self.resizable(False, False)
        self.transient(parent)
        self._build()
        self.update_idletasks()
        w, h = 360, 220
        sw   = self.winfo_screenwidth()
        sh   = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.grab_set()
        self.focus_force()

    def _build(self):
        frm = tk.Frame(self, padx=20, pady=16)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text="Concepto:", font=("Arial", 11), anchor="w").grid(
            row=0, column=0, sticky="w", pady=7)
        self.e_concepto = tk.Entry(frm, font=("Arial", 11), width=28)
        self.e_concepto.insert(0, self._item["concepto"])
        self.e_concepto.grid(row=0, column=1, padx=10, pady=7)

        tk.Label(frm, text="Monto ($):", font=("Arial", 11), anchor="w").grid(
            row=1, column=0, sticky="w", pady=7)
        self.e_monto = tk.Entry(frm, font=("Arial", 11), width=28)
        self.e_monto.insert(0, str(self._item["monto"]))
        self.e_monto.grid(row=1, column=1, padx=10, pady=7)

        tk.Label(frm, text="Fecha:", font=("Arial", 11), anchor="w").grid(
            row=2, column=0, sticky="w", pady=7)
        self.e_fecha = tk.Entry(frm, font=("Arial", 11), width=28)
        self.e_fecha.insert(0, self._item["fecha"])
        self.e_fecha.grid(row=2, column=1, padx=10, pady=7)

        btn_frame = tk.Frame(frm)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(14, 0))

        tk.Button(btn_frame, text="Guardar", command=self._guardar,
                  font=("Arial", 11, "bold"), bg="#1565C0", fg="white",
                  relief="flat", cursor="hand2", padx=18).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Cancelar", command=self.destroy,
                  font=("Arial", 11), relief="flat", cursor="hand2",
                  padx=12).pack(side="left", padx=6)

    def _guardar(self):
        concepto = self.e_concepto.get().strip()
        if not concepto:
            messagebox.showerror("Campo requerido", "El concepto no puede estar vacío.", parent=self)
            return
        try:
            monto = float(self.e_monto.get().strip())
            if monto <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Monto inválido", "Ingresa un monto positivo.", parent=self)
            return
        self._item["concepto"] = concepto
        self._item["monto"]    = monto
        self._item["fecha"]    = self.e_fecha.get().strip()
        self._callback()
        self.destroy()


class SeguimientoGastos(tk.Frame):
    """Seguimiento de pago de gastos del mes con informe pagado / pendiente."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._items: list[dict] = []   # {concepto, monto, fecha, pagado}
        self._construir_ui()

    # ------------------------------------------------------------------ UI --

    def _construir_ui(self):
        # Barra superior
        topbar = tk.Frame(self, pady=4)
        topbar.pack(fill="x", padx=8)
        tk.Button(topbar, text="← Volver",
                  command=lambda: self.controller.show_frame("MenuPrincipal"),
                  font=("Arial", 9), relief="flat", cursor="hand2",
                  fg="#1565C0").pack(side="left")
        tk.Button(topbar, text="↺ Importar registro del mes",
                  command=self._importar_desde_registro,
                  font=("Arial", 9), relief="flat", cursor="hand2",
                  fg="#555555").pack(side="right")

        tk.Label(self, text="Gastos del Mes — Seguimiento",
                 font=("Arial", 15, "bold")).pack(pady=(4, 2))
        self.subtitulo = tk.Label(self, text="—", font=("Arial", 10), fg="#777777")
        self.subtitulo.pack(pady=(0, 6))

        # Formulario para agregar ítem manual
        form = tk.Frame(self, padx=16)
        form.pack(fill="x")
        tk.Label(form, text="Concepto:", font=("Arial", 10)).grid(
            row=0, column=0, sticky="w", padx=(0, 4), pady=4)
        self.e_nuevo_concepto = tk.Entry(form, font=("Arial", 10), width=26)
        self.e_nuevo_concepto.grid(row=0, column=1, padx=4, pady=4)
        tk.Label(form, text="Monto ($):", font=("Arial", 10)).grid(
            row=0, column=2, sticky="w", padx=(8, 4), pady=4)
        self.e_nuevo_monto = tk.Entry(form, font=("Arial", 10), width=10)
        self.e_nuevo_monto.grid(row=0, column=3, padx=4, pady=4)
        tk.Button(form, text="+ Agregar", command=self._agregar_item,
                  font=("Arial", 10, "bold"), bg="#2E7D32", fg="white",
                  relief="flat", cursor="hand2", padx=10).grid(row=0, column=4, padx=8)

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=16, pady=(4, 0))

        # Tabla
        tabla_frame = tk.Frame(self, padx=16)
        tabla_frame.pack(fill="both", expand=True, pady=(4, 0))

        cols = ("estado", "concepto", "monto", "fecha")
        self.tabla = ttk.Treeview(tabla_frame, columns=cols,
                                  show="headings", height=10)
        self.tabla.heading("estado",   text="Estado",   anchor="center")
        self.tabla.heading("concepto", text="Concepto", anchor="w")
        self.tabla.heading("monto",    text="Monto",    anchor="e")
        self.tabla.heading("fecha",    text="Fecha",    anchor="center")
        self.tabla.column("estado",    width=100, anchor="center", stretch=False)
        self.tabla.column("concepto",  width=280, anchor="w")
        self.tabla.column("monto",     width=120, anchor="e",  stretch=False)
        self.tabla.column("fecha",     width=95,  anchor="center", stretch=False)

        sb = ttk.Scrollbar(tabla_frame, orient="vertical",
                           command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=sb.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.tabla.tag_configure("pagado",
                                 background="#E8F5E9", foreground="#1B5E20")
        self.tabla.tag_configure("pendiente",
                                 background="#FFEBEE", foreground="#B71C1C")

        # Botones de acción
        acc = tk.Frame(self, padx=16)
        acc.pack(fill="x", pady=(6, 0))

        tk.Button(acc, text="✓  Marcar pagado / pendiente",
                  command=self._toggle_pagado,
                  font=("Arial", 10), bg="#2E7D32", fg="white",
                  relief="flat", cursor="hand2", padx=10).pack(side="left", padx=(0, 6))
        tk.Button(acc, text="✎  Editar",
                  command=self._editar_item,
                  font=("Arial", 10), bg="#1565C0", fg="white",
                  relief="flat", cursor="hand2", padx=10).pack(side="left", padx=(0, 6))
        tk.Button(acc, text="✕  Eliminar",
                  command=self._eliminar_item,
                  font=("Arial", 10), bg="#C62828", fg="white",
                  relief="flat", cursor="hand2", padx=10).pack(side="left")
        tk.Button(acc, text="Guardar",
                  command=self._guardar,
                  font=("Arial", 10, "bold"), bg="#37474F", fg="white",
                  relief="flat", cursor="hand2", padx=14).pack(side="right")

        # Separador e informe
        ttk.Separator(self, orient="horizontal").pack(
            fill="x", padx=16, pady=(10, 6))

        inf = tk.Frame(self, padx=20, pady=2)
        inf.pack(fill="x")

        tk.Label(inf, text="Informe del mes",
                 font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 4))

        self.lbl_pagado = tk.Label(inf, text="✓  Pagado:      0 concepto(s) — $0.00",
                                   font=("Arial", 11), fg="#2E7D32", anchor="w")
        self.lbl_pagado.pack(fill="x")

        self.lbl_pendiente = tk.Label(inf,
                                      text="○  Pendiente:  0 concepto(s) — $0.00",
                                      font=("Arial", 11), fg="#C62828", anchor="w")
        self.lbl_pendiente.pack(fill="x")

        self.lbl_total = tk.Label(inf, text="     Total:               $0.00",
                                  font=("Arial", 12, "bold"), anchor="w")
        self.lbl_total.pack(fill="x", pady=(4, 8))

    # --------------------------------------------------------------- datos --

    def cargar_datos(self):
        """Llamado automáticamente al mostrar el frame."""
        self._items = []
        m, y = self.controller.mes_activo
        mes_key = f"{m:02d}/{y}"
        mes_label = f"{MESES_ES[m]} {y}"

        if os.path.exists(ARCHIVO_SEGUIMIENTO):
            with open(ARCHIVO_SEGUIMIENTO, "r", encoding="utf-8") as f:
                raw = json.load(f)

            # Migración: formato antiguo (clave "mes" en raíz) → nuevo multi-mes
            if "mes" in raw and "items" in raw:
                mk_viejo = raw.get("guardado_en", "")
                try:
                    dt = datetime.strptime(mk_viejo, "%d/%m/%Y %H:%M:%S")
                    mk_viejo = f"{dt.month:02d}/{dt.year}"
                except ValueError:
                    mk_viejo = mes_key
                raw = {mk_viejo: {"mes": raw["mes"],
                                  "guardado_en": raw.get("guardado_en", ""),
                                  "items": raw["items"]}}
                with open(ARCHIVO_SEGUIMIENTO, "w", encoding="utf-8") as f:
                    json.dump(raw, f, ensure_ascii=False, indent=2)

            if mes_key in raw:
                self._items = raw[mes_key].get("items", [])
                self.subtitulo.config(text=mes_label)
                self._refrescar_tabla()
                return

        # Sin datos para este mes → intentar importar desde gastos.json
        self._importar_desde_registro(silent=True)

    def _importar_desde_registro(self, silent=False):
        """Carga los gastos de la última sesión del mes desde gastos.json."""
        if not os.path.exists(ARCHIVO_DATOS):
            if not silent:
                messagebox.showinfo("Sin datos",
                                    "No hay registro de gastos guardado.")
            return

        with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
            datos = json.load(f)

        m, y = self.controller.mes_activo
        mes_key = f"{m:02d}/{y}"
        sesiones_mes = []
        for reg in datos:
            try:
                if _mes_key(reg) == mes_key:
                    sesiones_mes.append(reg)
            except KeyError:
                pass

        if not sesiones_mes:
            if not silent:
                messagebox.showinfo(
                    "Sin datos",
                    f"No hay gastos registrados para "
                    f"{MESES_ES[m]} {y}.")
            return

        ultima = sesiones_mes[-1]
        self._items = [
            {"concepto": g["concepto"], "monto": g["monto"],
             "fecha": g["fecha"], "pagado": False}
            for g in ultima["gastos"]
        ]
        mes_label = f"{MESES_ES[m]} {y}"
        self.subtitulo.config(text=mes_label)
        self._refrescar_tabla()
        self._guardar(silent=True)

    # ------------------------------------------------------------- tabla ---

    def _refrescar_tabla(self):
        self.tabla.delete(*self.tabla.get_children())
        for i, item in enumerate(self._items):
            pagado = item.get("pagado", False)
            estado = "✓  Pagado" if pagado else "○  Pendiente"
            tag    = "pagado"    if pagado else "pendiente"
            self.tabla.insert("", "end", iid=str(i),
                              values=(estado, item["concepto"],
                                      f"${item['monto']:,.2f}",
                                      item.get("fecha", "")),
                              tags=(tag,))
        self._actualizar_informe()

    def _actualizar_informe(self):
        pagados    = [it for it in self._items if it.get("pagado")]
        pendientes = [it for it in self._items if not it.get("pagado")]
        tot_p = sum(it["monto"] for it in pagados)
        tot_n = sum(it["monto"] for it in pendientes)
        total = tot_p + tot_n

        self.lbl_pagado.config(
            text=f"✓  Pagado:      {len(pagados)} concepto(s) — ${tot_p:,.2f}")
        self.lbl_pendiente.config(
            text=f"○  Pendiente:  {len(pendientes)} concepto(s) — ${tot_n:,.2f}")
        self.lbl_total.config(
            text=f"     Total:               ${total:,.2f}")

    # ------------------------------------------------------------ acciones --

    def _selected_idx(self):
        sel = self.tabla.selection()
        if not sel:
            messagebox.showwarning("Sin selección",
                                   "Selecciona un elemento de la lista.")
            return None
        return int(sel[0])

    def _toggle_pagado(self):
        idx = self._selected_idx()
        if idx is None:
            return
        self._items[idx]["pagado"] = not self._items[idx].get("pagado", False)
        self._refrescar_tabla()
        if str(idx) in self.tabla.get_children():
            self.tabla.selection_set(str(idx))
            self.tabla.see(str(idx))

    def _agregar_item(self):
        concepto = self.e_nuevo_concepto.get().strip()
        if not concepto:
            messagebox.showerror("Campo requerido", "Escribe un concepto.")
            self.e_nuevo_concepto.focus()
            return
        try:
            monto = float(self.e_nuevo_monto.get().strip())
            if monto <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Monto inválido", "Ingresa un monto positivo.")
            self.e_nuevo_monto.focus()
            return
        self._items.append({
            "concepto": concepto,
            "monto":    monto,
            "fecha":    date.today().strftime("%d/%m/%Y"),
            "pagado":   False,
        })
        self.e_nuevo_concepto.delete(0, tk.END)
        self.e_nuevo_monto.delete(0, tk.END)
        self._refrescar_tabla()
        self.e_nuevo_concepto.focus()

    def _editar_item(self):
        idx = self._selected_idx()
        if idx is None:
            return
        _EditarGastoDialog(self, self._items[idx],
                           callback=self._refrescar_tabla)

    def _eliminar_item(self):
        idx = self._selected_idx()
        if idx is None:
            return
        nombre = self._items[idx]["concepto"]
        if not messagebox.askyesno("Confirmar eliminación",
                                   f"¿Eliminar «{nombre}»?"):
            return
        del self._items[idx]
        self._refrescar_tabla()

    def _guardar(self, silent=False):
        m, y = self.controller.mes_activo
        mes_key = f"{m:02d}/{y}"
        mes_label = f"{MESES_ES[m]} {y}"

        # Leer archivo existente (puede tener otros meses)
        if os.path.exists(ARCHIVO_SEGUIMIENTO):
            with open(ARCHIVO_SEGUIMIENTO, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # Migrar formato antiguo si es necesario
            if "mes" in raw and "items" in raw:
                raw = {}
        else:
            raw = {}

        raw[mes_key] = {
            "mes":         mes_label,
            "guardado_en": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "items":       self._items,
        }
        with open(ARCHIVO_SEGUIMIENTO, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        if not silent:
            pagados = sum(1 for it in self._items if it.get("pagado"))
            messagebox.showinfo(
                "Guardado",
                f"Seguimiento guardado — {mes_label}.\n"
                f"{pagados} de {len(self._items)} concepto(s) marcado(s) como pagado.")


# ---------------------------------------------------------------------------
root = tk.Tk()
AdministracionApp(root)
root.mainloop()
