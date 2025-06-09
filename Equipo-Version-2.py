import os
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI

try:
    from config import OPENAI_API_KEY

    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
except ImportError:
    raise ImportError("Please create a config.py with your OPENAI_API_KEY.")

# Define el modelo OpenAI
os.environ["OPENAI_MODEL_NAME"] = "gpt-3.5-turbo"  # o "gpt-4" si tienes acceso


llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.3)

# Agente para metadatos
metadatos_agent = Agent(
    role="Extraedor de metadatos de PDF",
    goal="Extraer título, autores, año, revista y DOI del PDF",
    backstory="Eres un experto académico que detecta metadatos incluso si no están bien formateados.",
    llm=llm,
)

# Agente que resume
resumidor = Agent(
    role="Resumidor académico en LaTeX",
    goal=(
        "Leer el contenido completo del artículo científico y generar un resumen "
        "estructurado y técnico en formato LaTeX. El resumen debe incluir los elementos clave: "
        "objetivo del estudio, metodología empleada, resultados principales y conclusiones más relevantes."
    ),
    backstory=(
        "Eres un experto académico especializado en generar resúmenes científicos en LaTeX. "
        "Tienes gran experiencia con redacción técnica clara, precisa y alineada a los estándares "
        "de publicaciones científicas. Siempre entregas el texto en formato LaTeX limpio, "
        "listo para ser integrado en artículos académicos o ponencias."
    ),
    llm=llm,
)
# Agente que redacta el artículo final
redactor = Agent(
    role="Redactor académico en LaTeX",
    goal=(
        "Redactar una sección del estado del arte académicamente sólida, integrando resúmenes previos "
        "y referencias en formato LaTeX. La redacción debe ser clara, precisa y bien estructurada, "
        "usando citas con comandos \\cite{{clave}} basados en los metadatos extraídos de cada artículo."
    ),
    backstory=(
        "Eres un redactor experto en publicaciones científicas. Tienes amplia experiencia escribiendo "
        "secciones de estado del arte para artículos académicos en LaTeX. Sabes cómo organizar los "
        "resúmenes y las referencias bibliográficas para dar contexto sólido a una investigación. "
        "Entiendes cómo citar correctamente usando BibTeX."
    ),
    llm=llm,
)








import fitz, re, requests

def extraer_texto_de_pdf(path):
    doc = fitz.open(path)
    return "\n".join(p.get_text() for p in doc)

def buscar_doi_crossref_por_titulo(titulo):
    try:
        resp = requests.get("https://api.crossref.org/works", params={"query.title": titulo, "rows": 1}, timeout=10)
        item = resp.json().get("message", {}).get("items", [])[0]
        return item.get("DOI")
    except: return None

def obtener_bibtex_de_doi(doi):
    try:
        resp = requests.get(f"https://doi.org/{doi}", headers={"Accept": "application/x-bibtex"}, timeout=10)
        return resp.text if resp.status_code==200 else None
    except: return None






carpeta_pdf = "Articulos_de_Prueba"
resumenes = []
import os


open("referencias.bib", "w").close()  # Limpia el archivo antes de iniciar
for archivo in os.listdir(carpeta_pdf):
    if not archivo.lower().endswith(".pdf"): continue
    ruta = os.path.join(carpeta_pdf, archivo)
    texto = extraer_texto_de_pdf(ruta)

    # 4.1 Extraer metadatos
    task_meta = Task(
        description=f"Extrae metadatos clave de este artículo (título, autores, año, revista, DOI):\n\n{texto}",
        expected_output="Metadatos en formato JSON o estructurado.",
        agent=metadatos_agent,
    )
    meta = str(Crew(agents=[metadatos_agent], tasks=[task_meta], verbose=False).kickoff())

    # Intentar recuperar DOI si falta
    match = re.search(r'DOI[:\s]*10\.\d{4,9}/\S+', meta, re.I)
    doi = match.group(0).split()[-1] if match else None
    if not doi:
        # extraer posible título
        title_cand = texto.split("\n")[0]
        doi = buscar_doi_crossref_por_titulo(title_cand)
    bibtex = obtener_bibtex_de_doi(doi) if doi else None

    # 4.2 Obtener resumen
    task_res = Task(
        description=f"""Resume el siguiente artículo científico de forma estructurada y en formato LaTeX.

    Debes incluir:

    - \textbf{{Objetivo del estudio}}
    - \textbf{{Metodología}}
    - \textbf{{Resultados principales}}
    - \textbf{{Conclusiones clave}}

    Texto del artículo:
    \n\n{texto}

    """,
        expected_output="Resumen técnico en formato LaTeX.",
        agent=resumidor,
    )


    resumen = str(Crew(agents=[resumidor], tasks=[task_res], verbose=False).kickoff())

    # Guardamos info temporal
    resumenes.append({
        "archivo": archivo,
        "metadata": meta,
        "doi": doi,
        "bibtex": bibtex,
        "resumen": resumen
    })

    # Guardar en txt
    with open("resumenes_articulos.txt", "a", encoding="utf-8") as f:
        f.write(f"=== {archivo} ===\n")
        f.write("Metadatos:\n" + meta + "\n\n")
        f.write("Resumen:\n" + resumen + "\n\n")
        f.write("BibTeX:\n" + (bibtex or "No disponible") + "\n")
        f.write("="*80 + "\n\n")

    # Guardar BibTeX por separado
    if bibtex:
        with open("referencias.bib", "a", encoding="utf-8") as f_bib:
            f_bib.write(bibtex + "\n\n")



all_res = "\n\n".join(
    f"{r['resumen']}\n{r['bibtex'] or ''}"
    for r in resumenes
)

task_write = Task(
    description=(
        "Redacta una sección del estado del arte en LaTeX utilizando los siguientes resúmenes académicos "
        "y sus respectivas claves BibTeX. Cada resumen pertenece a un artículo diferente, y debe integrarse "
        "de forma fluida en el texto. Asegúrate de citar correctamente usando \\cite{clave}. "
        "No incluyas la bibliografía completa, solo las citas dentro del texto."
        "\n\nResúmenes y claves BibTeX:\n" + all_res
    ),
    expected_output="Sección redactada en LaTeX con citas bien ubicadas.",
    agent=redactor,
)


final = str(Crew(agents=[redactor], tasks=[task_write], verbose=True).kickoff())

# Mostrar en pantalla
print("\n📘 Sección del estado del arte generada:\n")
print(final)

# Guardar salida
with open("articulo_final.txt","w",encoding="utf-8") as f:
    f.write(final)

print("📝 Artículo final guardado en articulo_final.txt")




