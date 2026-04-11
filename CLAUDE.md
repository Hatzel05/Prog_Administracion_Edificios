# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
python administracion.py
```

Requires Python 3 with `tkinter` available (included in most standard Python installations on Linux via `python3-tk`).

## Architecture

Single-file desktop app built with `tkinter`. The entire application lives in one class:

- `AdministracionEdificio` — owns both the UI and the in-memory data (`self.gastos: list[dict]`). There is no persistence layer; data resets on close.
- `_construir_ui()` — called once from `__init__`, builds all widgets. Widgets that need to be updated later (the `Treeview` table and the total `Label`) are stored as instance attributes (`self.tabla`, `self.total_label`).
- `_agregar_gasto()` — the only method with logic: validates inputs, appends to `self.gastos`, inserts a row into the `Treeview`, and recalculates the total via a generator expression over `self.gastos`.

The three lines at module level (`tk.Tk()`, instantiation, `mainloop()`) are the entry point.
