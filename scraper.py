import os
import sys
import csv
import threading
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from questionary import select

CSV_FILENAME = "noticias.csv"

# ========= DRIVER =========
def drivers_disponibles():
    disponibles = []
    if os.path.exists("msedgedriver.exe"):
        disponibles.append("Edge")
    if os.path.exists("geckodriver.exe"):
        disponibles.append("Firefox")
    return disponibles

def obtener_driver(navegador):
    if navegador == "Edge":
        options = EdgeOptions()
        options.add_argument("--headless")
        service = EdgeService("msedgedriver.exe")
        return webdriver.Edge(service=service, options=options)

    elif navegador == "Firefox":
        options = FirefoxOptions()
        options.add_argument("--headless")
        service = FirefoxService("geckodriver.exe")
        return webdriver.Firefox(service=service, options=options)

# ========= SCRAPER =========
def scrapear_infobae(driver):
    noticias = []
    wait = WebDriverWait(driver, 5)
    driver.get("https://www.infobae.com")
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "a")))

    enlaces = driver.find_elements(By.TAG_NAME, "a")
    urls = []
    for enlace in enlaces:
        href = enlace.get_attribute("href")
        if href and "/2025/" in href and href.startswith("https://www.infobae.com"):
            if href not in urls:
                urls.append(href)
        if len(urls) >= 5:
            break

    for url in urls:
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

        try:
            titulo = driver.find_element(By.TAG_NAME, "h1").text.strip()
        except:
            titulo = "Sin título"

        try:
            bajada = driver.find_element(By.TAG_NAME, "h2").text.strip()
        except:
            try:
                bajada = driver.find_element(By.TAG_NAME, "p").text.strip()
            except:
                bajada = "Sin bajada"

        fecha = datetime.now().strftime("%H:%M %d-%m-%Y")

        noticias.append({
            "Título": titulo,
            "Bajada": bajada,
            "URL": url,
            "Fecha y hora": fecha
        })

    return noticias

# ========= CSV =========
def guardar_csv(noticias):
    existe = os.path.isfile(CSV_FILENAME)
    noticias_existentes = []

    if existe:
        with open(CSV_FILENAME, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            noticias_existentes = [row["URL"] for row in reader]

    noticias_filtradas = [n for n in noticias if n["URL"] not in noticias_existentes]

    if not noticias_filtradas:
        return False  # No se agregó nada

    with open(CSV_FILENAME, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Título", "Bajada", "URL", "Fecha y hora"])
        if not existe:
            writer.writeheader()
        writer.writerows(noticias_filtradas)
    
    return True

def leer_fechas_disponibles():
    if not os.path.isfile(CSV_FILENAME):
        return []
    with open(CSV_FILENAME, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return sorted(set(row["Fecha y hora"][-10:] for row in reader))

def leer_noticias_por_fecha(fecha):
    noticias = []
    with open(CSV_FILENAME, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Fecha y hora"].endswith(fecha):
                noticias.append(row)
    return noticias

# ========= GUI =========
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Scraper de Noticias")
        self.geometry("800x600")

        ctk.set_default_color_theme("blue")

        self.label = ctk.CTkLabel(self, text="Scraper de Noticias", font=("Arial", 24, "bold"))
        self.label.pack(pady=20)

        self.navegador_var = ctk.StringVar(value="Edge")
        self.navegador_menu = ctk.CTkOptionMenu(self, values=["Edge", "Firefox"], variable=self.navegador_var)
        self.navegador_menu.pack(pady=10)

        self.boton_scrapear = ctk.CTkButton(self, text="Scrapear Infobae", command=self.iniciar_scraping)
        self.boton_scrapear.pack(pady=10)

        self.boton_leer = ctk.CTkButton(self, text="Leer Noticias Guardadas", command=self.leer_noticias)
        self.boton_leer.pack(pady=5)

        self.spinner = ctk.CTkLabel(self, text="", font=("Arial", 16))
        self.spinner.pack(pady=10)

        self.scroll_frame = ctk.CTkScrollableFrame(self, width=700, height=350)
        self.scroll_frame.pack(pady=10)

        self.spinner_active = False

    def iniciar_scraping(self):
        self.spinner.configure(text="⏳ Cargando noticias")
        self.clear_scroll()
        self.spinner_active = True
        threading.Thread(target=self.animate_spinner).start()
        threading.Thread(target=self.scrapear).start()

    def scrapear(self):
        navegador = self.navegador_var.get()
        try:
            driver = obtener_driver(navegador)
            noticias = scrapear_infobae(driver)
            driver.quit()
            hubo_nuevas = guardar_csv(noticias)
            self.spinner_active = False
            if not noticias:
                self.spinner.configure(text="⚠️ No se encontraron noticias.")
            elif not hubo_nuevas:
                self.spinner.configure(text="⚠️ Ya estaban guardadas.")
            else:
                self.spinner.configure(text="✅ Noticias cargadas")
                self.mostrar_noticias(noticias)
        except Exception as e:
            self.spinner_active = False
            self.spinner.configure(text="❌ Error al scrapear.")
            messagebox.showerror("Error", str(e))

    def mostrar_noticias(self, noticias):
        self.clear_scroll()
        for n in noticias:
            titulo = ctk.CTkLabel(self.scroll_frame, text=f"📰 {n['Título']}", font=("Arial", 16, "bold"), wraplength=680, anchor="w", justify="left")
            bajada = ctk.CTkLabel(self.scroll_frame, text=n['Bajada'], font=("Arial", 14), wraplength=680, anchor="w", justify="left")
            url = ctk.CTkLabel(self.scroll_frame, text=n['URL'], font=("Arial", 12, "italic"), wraplength=680, anchor="w", justify="left")
            fecha = ctk.CTkLabel(self.scroll_frame, text=n['Fecha y hora'], font=("Arial", 12), wraplength=680, anchor="w", justify="left")
            sep = ctk.CTkLabel(self.scroll_frame, text="-"*100)
            for w in [titulo, bajada, url, fecha, sep]:
                w.pack(anchor="w", padx=10, pady=2)

    def leer_noticias(self):
        fechas = leer_fechas_disponibles()
        if not fechas:
            messagebox.showinfo("Info", "No hay noticias guardadas.")
            return

        # Crear ventana emergente para elegir la fecha
        ventana = ctk.CTkToplevel(self)
        ventana.title("Elegir fecha")
        ventana.geometry("300x150")
        ventana.transient(self)  # La asocia a la ventana principal
        ventana.grab_set()       # La hace modal: bloquea la principal
        ventana.focus_force()    # Le da foco automáticamente

        label = ctk.CTkLabel(ventana, text="Seleccioná una fecha:", font=("Arial", 14))
        label.pack(pady=10)

        fecha_var = ctk.StringVar(value=fechas[0])
        menu = ctk.CTkOptionMenu(ventana, values=fechas, variable=fecha_var)
        menu.pack(pady=10)

        def confirmar():
            fecha = fecha_var.get()
            noticias = leer_noticias_por_fecha(fecha)
            self.mostrar_noticias(noticias)
            ventana.destroy()

        boton = ctk.CTkButton(ventana, text="Mostrar noticias", command=confirmar)
        boton.pack(pady=10)

    def clear_scroll(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

    def animate_spinner(self):
        puntos = ""
        while self.spinner_active:
            puntos = "." if puntos == "..." else puntos + "."
            self.spinner.configure(text=f"⏳ Cargando noticias{puntos}")
            self.spinner.update_idletasks()
            threading.Event().wait(0.4)

# ========= MAIN =========
if __name__ == "__main__":
    if len(sys.argv) > 1:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--cli", action="store_true", help="Ejecutar en modo consola")
        args = parser.parse_args()

        if args.cli:
            disponibles = drivers_disponibles()
            if not disponibles:
                print("No se encontró ningún driver disponible.")
                sys.exit(1)
            navegador = select("Elegí el navegador:", choices=disponibles).ask()
            driver = obtener_driver(navegador)
            noticias = scrapear_infobae(driver)
            driver.quit()
            hubo_nuevas = guardar_csv(noticias)
            for n in noticias:
                print(f"\n📰 {n['Título']}\n{n['Bajada']}\n{n['URL']}\n{n['Fecha y hora']}\n{'-'*50}")
            if not hubo_nuevas:
                print("\n⚠️ No se agregaron noticias nuevas.")
        else:
            App().mainloop()
    else:
        App().mainloop()
