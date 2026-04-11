import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date


class AdministracionEdificio:
    def __init__(self, root):
        self.root = root
        self.root.title("Administración del Edificio")
        self.root.geometry("620x520")
        self.root.resizable(False, False)

        self.gastos = []
        self.fecha_desbloqueada = False

        self._construir_ui()

    def _construir_ui(self):
        # --- Encabezado ---
        tk.Label(
            self.root,
            text="Registro de Gastos",
            font=("Arial", 16, "bold"),
        ).pack(pady=(16, 8))

        # --- Formulario ---
        form = tk.Frame(self.root, padx=24, pady=8)
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
        self.fecha_entry = tk.Entry(form, font=("Arial", 11), width=28)
        self.fecha_entry.insert(0, date.today().strftime("%d/%m/%Y"))
        self.fecha_entry.config(state="readonly")
        self.fecha_entry.grid(row=2, column=1, padx=10, pady=6, sticky="w")
        self.fecha_btn = tk.Button(
            form,
            text="Editar",
            command=self._toggle_fecha,
            font=("Arial", 9),
            width=7,
            cursor="hand2",
        )
        self.fecha_btn.grid(row=2, column=2, padx=(0, 10), pady=6)

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
        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=20, pady=4)

        # --- Tabla de gastos ---
        tabla_frame = tk.Frame(self.root, padx=20)
        tabla_frame.pack(fill="both", expand=True)

        tk.Label(tabla_frame, text="Gastos del mes", font=("Arial", 11, "bold")).pack(
            anchor="w", pady=(6, 4)
        )

        cols = ("fecha", "concepto", "monto")
        self.tabla = ttk.Treeview(tabla_frame, columns=cols, show="headings", height=10)
        self.tabla.heading("fecha", text="Fecha")
        self.tabla.heading("concepto", text="Concepto")
        self.tabla.heading("monto", text="Monto")
        self.tabla.column("fecha", width=100, anchor="center")
        self.tabla.column("concepto", width=300, anchor="w")
        self.tabla.column("monto", width=140, anchor="e")
        self.tabla.pack(fill="both", expand=True)

        # --- Total y cuota por departamento ---
        self.total_label = tk.Label(
            self.root,
            text="Total:  $0.00",
            font=("Arial", 12, "bold"),
            anchor="e",
        )
        self.total_label.pack(fill="x", padx=24, pady=(12, 2))

        self.cuota_label = tk.Label(
            self.root,
            text="Por departamento (÷20):  $0.00",
            font=("Arial", 11),
            anchor="e",
            fg="#555555",
        )
        self.cuota_label.pack(fill="x", padx=24, pady=(0, 12))

        # Foco inicial
        self.concepto_combo.focus()

    def _toggle_fecha(self):
        if self.fecha_desbloqueada:
            self.fecha_entry.config(state="readonly")
            self.fecha_btn.config(text="Editar")
            self.fecha_desbloqueada = False
        else:
            self.fecha_entry.config(state="normal")
            self.fecha_btn.config(text="Bloquear")
            self.fecha_desbloqueada = True
            self.fecha_entry.focus()

    def _on_concepto_select(self, event=None):
        if self.concepto_var.get() == "Otros":
            self.concepto_otro.config(state="normal")
            self.concepto_otro.focus()
        else:
            self.concepto_otro.delete(0, tk.END)
            self.concepto_otro.config(state="disabled")

    def _agregar_gasto(self):
        seleccion = self.concepto_var.get()
        if seleccion == "Otros":
            concepto = self.concepto_otro.get().strip()
        else:
            concepto = seleccion

        fecha = self.fecha_entry.get().strip() if self.fecha_desbloqueada else date.today().strftime("%d/%m/%Y")
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
        self.cuota_label.config(text=f"Por departamento (÷20):  ${total / 20:,.2f}")

        self.concepto_var.set("")
        self.concepto_otro.delete(0, tk.END)
        self.concepto_otro.config(state="disabled")
        self.fecha_entry.config(state="normal")
        self.fecha_entry.delete(0, tk.END)
        self.fecha_entry.insert(0, date.today().strftime("%d/%m/%Y"))
        self.fecha_entry.config(state="readonly")
        self.fecha_btn.config(text="Editar")
        self.fecha_desbloqueada = False
        self.monto_entry.delete(0, tk.END)
        self.concepto_combo.focus()


root = tk.Tk()
AdministracionEdificio(root)
root.mainloop()
