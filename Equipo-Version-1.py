import os
import fitz  # PyMuPDF
from langchain_openai import ChatOpenAI
from crewai import Agent, Task, Crew
import requests
import re


try:
    from config import OPENAI_API_KEY

    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
except ImportError:
    raise ImportError("Please create a config.py with your OPENAI_API_KEY.")

# Define el modelo OpenAI
os.environ["OPENAI_MODEL_NAME"] = "gpt-3.5-turbo"  # o "gpt-4" si tienes acceso

# === Función para extraer texto de un PDF ===
def extraer_texto_de_pdf(ruta_pdf):
    doc = fitz.open(ruta_pdf)
    texto = ""
    for pagina in doc:
        texto += pagina.get_text()
    return texto


import fitz  # PyMuPDF
import re

##def extraer_doi(pdf_path):
#    with fitz.open(pdf_path) as doc:
#        for page in doc:
#            text = page.get_text()
#            match = re.search(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', text, re.I)
#            if match:
#                return match.group(0)
#    return None






import requests

def buscar_doi_por_titulo(titulo):
    url = "https://api.crossref.org/works"
    params = {"query.title": titulo, "rows": 1}
    try:
        respuesta = requests.get(url, params=params, timeout=10)
        data = respuesta.json()
        items = data.get("message", {}).get("items", [])
        if items:
            return items[0].get("DOI")
    except Exception as e:
        print(f"Error buscando DOI por título: {e}")
    return None

def obtener_bibtex_desde_doi(doi):
    if doi is None:
        return None
    headers = {"Accept": "application/x-bibtex"}
    url = f"https://doi.org/{doi}"
    try:
        respuesta = requests.get(url, headers=headers, timeout=10)
        if respuesta.status_code == 200:
            return respuesta.text
    except Exception as e:
        print(f"Error obteniendo BibTeX desde DOI: {e}")
    return None





def extraer_doi(texto):
    # Patrón para capturar DOIs más ampliamente
    patron_doi = re.compile(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', re.IGNORECASE)
    coincidencias = patron_doi.findall(texto)
    return coincidencias[0] if coincidencias else None




def obtener_bibtex(doi):
    url = f"https://api.crossref.org/works/{doi}/transform/application/x-bibtex"
    response = requests.get(url)
    if response.status_code == 200:
        return response.text.strip()
    return None



# === Inicializar LLM ===
llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.3)

# === Agentes ===
resumidor = Agent(
    role="Investigador de contenido",
    goal="Leer artículos científicos y extraer información clave",
    backstory="Eres un investigador experto en analizar literatura científica y encontrar ideas clave.",
    llm=llm,
)

redactor = Agent(
    role="Redactor técnico",
    goal="Redactar un artículo técnico claro y coherente con referencias incluidas",
    backstory="Eres un redactor técnico que transforma múltiples resúmenes en un texto estructurado, incluyendo referencias al final si las detectas.",
    llm=llm,
)

# === Ruta de PDFs ===
carpeta_pdf = "Articulos_de_Prueba"
resumenes = []
resumenes_guardar = []

print("📄 Resumiendo artículos científicos...\n")

for archivo in os.listdir(carpeta_pdf):
    if archivo.endswith(".pdf"):
        ruta = os.path.join(carpeta_pdf, archivo)
        texto_pdf = extraer_texto_de_pdf(ruta)

        # Crear tarea para resumir
        task_resumir = Task(
            description=f"Lee el siguiente artículo científico y genera un resumen claro. Si se encuentran referencias, inclúyelas al final del resumen:\n\n{texto_pdf}",
            expected_output="Resumen breve con hallazgos principales y referencias si las hay.",
            agent=resumidor,
        )

        # Ejecutar tarea de resumen
        crew_resumir = Crew(agents=[resumidor], tasks=[task_resumir], verbose=False)
        resumen = crew_resumir.kickoff()
        resumen_str = str(resumen)

        resumen_texto = f"=== Resumen de {archivo} ===\n{resumen_str}\n"

#        # 👉 Extraer DOI y BibTeX (si se encuentra)
#        doi = extraer_doi(ruta)
#        if not doi:
#            print(f"[⚠️] No se encontró DOI en {archivo}")
#            print("Fragmento del texto:\n", texto_pdf[:1000])  # Muestra las primeras 1000 letras
#        bibtex = obtener_bibtex(doi) if doi else None

        # Intentar extraer título (puedes refinar esta parte)
        primeras_lineas = texto_pdf.strip().split("\n")[:10]
        titulo_candidato = max(primeras_lineas, key=len)

        doi = extraer_doi(texto_pdf)
        if not doi:
            doi = buscar_doi_por_titulo(titulo_candidato)

        bibtex = obtener_bibtex_desde_doi(doi)



        # 👉 Guardar resumen + BibTeX en archivo
        with open("resumenes_articulos.txt", "a", encoding="utf-8") as f:
            f.write(f"📄 Archivo: {archivo}\n")
            f.write("Resumen del artículo:\n")
            f.write(resumen_str + "\n\n")
            if bibtex:
                f.write("BibTeX:\n")
                f.write(bibtex + "\n")
            f.write("\n" + "=" * 80 + "\n")

        # Guardar para redacción final
        resumenes.append(resumen_str)
        resumenes_guardar.append(resumen_texto)

# === Guardar resúmenes en archivo .txt ===
archivo_resumenes = "resumenes_articulos.txt"
with open(archivo_resumenes, "w", encoding="utf-8") as f:
    f.write("\n\n".join(resumenes_guardar))

print(f"📝 Resúmenes guardados en: {archivo_resumenes}")

# === Unir todos los resúmenes para la redacción final ===
todos_los_resumenes = "\n\n".join(resumenes)

# === Crear tarea de redacción final ===
task_redactar = Task(
    description=f"Con base en los siguientes resúmenes de artículos científicos, redacta un solo texto técnico con introducción, desarrollo y conclusión. Si encuentras referencias, inclúyelas al final en una sección de 'Referencias':\n\n{todos_los_resumenes}",
    expected_output="Artículo final redactado con referencias incluidas si se encuentran.",
    agent=redactor,
)

crew_redactar = Crew(agents=[redactor], tasks=[task_redactar], verbose=True)
#resultado_final = crew_redactar.kickoff()
resultado_final = str(crew_redactar.kickoff())

# === Mostrar el resultado final ===
print("\n✅ ARTÍCULO FINAL REDACTADO:\n")
print(resultado_final)

# (Opcional) Guardar el artículo final en un archivo .txt
with open("articulo_final_redactado.txt", "w", encoding="utf-8") as f:
    f.write(resultado_final)