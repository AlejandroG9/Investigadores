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
        "estructurado y técnico en formato para incertar en LaTeX. El resumen debe incluir los elementos clave: "
        "objetivo del estudio, metodología empleada, resultados principales y conclusiones más relevantes. "
        "Debe limitarse exclusivamente a la información contenida en el texto, sin agregar ni inferir contenido externo."
    ),
    backstory=(
        "Eres un experto académico especializado en generar resúmenes científicos en LaTeX. "
        "Tienes gran experiencia con redacción técnica clara, precisa y alineada a los estándares "
        "de publicaciones científicas. Siempre entregas el texto en formato LaTeX limpio, "
        "listo para ser integrado en artículos académicos o ponencias. "
        "Importante: no debes incluir ninguna información que no esté explícitamente presente en el documento leído."
    ),
    llm=llm,
)

# Agente que redacta el artículo final
redactor = Agent(
    role="Redactor académico en LaTeX",
    goal=(
        "Redactar una sección del estado del arte académicamente sólida, integrando resúmenes previos "
        "y referencias en formato LaTeX. La redacción debe ser clara, precisa y bien estructurada, "
        "usando citas con comandos \\cite{{clave}} basados en los metadatos extraídos de cada artículo. "
        "No debe añadirse información que no provenga directamente de los resúmenes y metadatos disponibles."
    ),
    backstory=(
        "Eres un redactor experto en publicaciones científicas. Tienes amplia experiencia escribiendo "
        "secciones de estado del arte para artículos académicos en LaTeX. Sabes cómo organizar los "
        "resúmenes y las referencias bibliográficas para dar contexto sólido a una investigación. "
        "Entiendes cómo citar correctamente usando BibTeX. Importante: todo el contenido que generes debe derivarse exclusivamente "
        "de los resúmenes y metadatos provistos; no debes agregar contexto externo ni interpretaciones adicionales."
    ),
    llm=llm,
)



#=========Utilidades ===========
import fitz, re, requests
#def extraer_texto_de_pdf(path):
#    import fitz
#    doc = fitz.open(path)
#    texto = ""
#    for i, page in enumerate(doc):
#        try:
#            contenido = page.get_text("text").strip()
#            if not contenido:
#                print(f"⚠️ Página {i+1} sin texto en {path}")
#            texto += contenido + "\n"
#        except Exception as e:
#            print(f"❌ Error en página {i+1} de {path}: {e}")
#    return texto






def extraer_texto_de_pdf(path: str, umbral_minimo: int = 1000) -> str:
    texto_total = ""

    # 1. PyMuPDF (fitz)
    try:
        import fitz
        doc = fitz.open(path)
        texto = ""
        for i, page in enumerate(doc):
            contenido = page.get_text("text").strip()
            if not contenido:
                print(f"⚠️ Página {i+1} vacía en {path}")
            texto += contenido + "\n"
        doc.close()
        if len(texto.strip()) >= umbral_minimo:
            print(f"✅ Texto extraído con PyMuPDF: {len(texto)} caracteres")
            return texto
        else:
            print(f"❌ PyMuPDF extrajo poco texto ({len(texto)} caracteres)")
    except Exception as e:
        print(f"❌ Error con PyMuPDF: {e}")

    # 2. pdfminer.six
    try:
        from pdfminer.high_level import extract_text
        texto = extract_text(path)
        if len(texto.strip()) >= umbral_minimo:
            print(f"✅ Texto extraído con pdfminer: {len(texto)} caracteres")
            return texto
        else:
            print(f"❌ pdfminer extrajo poco texto ({len(texto)} caracteres)")
    except Exception as e:
        print(f"❌ Error con pdfminer: {e}")

    # 3. PyPDF2
    try:
        import PyPDF2
        texto = ""
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for i, page in enumerate(reader.pages):
                contenido = page.extract_text() or ""
                texto += contenido + "\n"
        if len(texto.strip()) >= umbral_minimo:
            print(f"✅ Texto extraído con PyPDF2: {len(texto)} caracteres")
            return texto
        else:
            print(f"❌ PyPDF2 extrajo poco texto ({len(texto)} caracteres)")
    except Exception as e:
        print(f"❌ Error con PyPDF2: {e}")

    print(f"⚠️ No se pudo extraer texto útil de {path}")
    return ""  # Fallo total


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









def procesar_articulos(carpeta_pdf: str, enfoque_resumen: str, seccion:str) -> list:
    resumenes = []
    open("referencias.bib", "w").close()  # Limpiar bib
    MIN_TEXTO_LONGITUD = 1000
    for archivo in os.listdir(carpeta_pdf):
        if not archivo.lower().endswith(".pdf"):
            continue
        ruta = os.path.join(carpeta_pdf, archivo)
        texto = extraer_texto_de_pdf(ruta)

        if not texto.strip():
            print(f"⚠️ Advertencia: El archivo {archivo} no tiene texto extraído válido.")
            continue

        print(f"{archivo}: longitud del texto extraído = {len(texto)}")
        if len(texto.strip()) < MIN_TEXTO_LONGITUD:
            print(f"⚠️ Texto insuficiente en {archivo}, saltando resumen.")
            resumen = "No se pudo extraer texto suficiente del PDF para generar resumen."
            # Podrías también asignar metadatos vacíos o básicos aquí si quieres
            meta = "{}"
            doi = None
            bibtex = None
            with open("errores_pdf.log", "a") as f:
                f.write(f"{archivo}: solo {len(texto)} caracteres extraídos\n")
        else:
            # Aquí va tu código actual para extraer metadatos, DOI, bibtex y resumen
            # ...
            # ...
            #resumen = str(Crew(agents=[resumidor], tasks=[task_res], verbose=False).kickoff())

            #print(f"Procesando {archivo}, texto extraído (primeros 300 chars):\n{texto[:300]}")

            # 1. Metadatos
            texto_corto = texto#[:5000]  # truncamos para evitar problemas
            task_meta = Task(
                description=f"Extrae metadatos clave de este artículo (título, autores, año, revista, DOI):\n\n{texto_corto}",
                expected_output="Metadatos en formato JSON o estructurado.",
                agent=metadatos_agent,
            )
            meta = str(Crew(agents=[metadatos_agent], tasks=[task_meta], verbose=False).kickoff())

            print(f"Metadatos extraídos: {meta}")

            # 2. DOI y BibTeX
            match = re.search(r'DOI[:\s]*10\.\d{4,9}/\S+', meta, re.I)
            doi = match.group(0).split()[-1] if match else buscar_doi_crossref_por_titulo(texto.split("\n")[0])
            bibtex = obtener_bibtex_de_doi(doi) if doi else None

            # 3. Resumen con enfoque personalizado
            task_res = Task( description=f"""Resume el siguiente artículo científico para la sección {seccion}, enfocado en {enfoque_resumen} de forma estructurada y en formato LaTeX.
    
            Debes incluir:
            
            - \\textbf{{Objetivo del estudio}}
            - \\textbf{{Metodología}}
            - \\textbf{{Resultados principales}}
            - \\textbf{{Conclusiones clave}}
            
            Texto del artículo:
            
            {texto}
            """,
                expected_output="Resumen técnico en formato LaTeX.",
                agent=resumidor,
            )
            resumen = str(Crew(agents=[resumidor], tasks=[task_res], verbose=False).kickoff())

            print(f"Resumen generado (primeros 300 chars):\n{resumen[:300]}")

        resumenes.append({
            "archivo": archivo,
            "metadata": meta,
            "doi": doi,
            "bibtex": bibtex,
            "resumen": resumen
        })

    return resumenes







def generar_capitulo(resumenes: list, capitulo: str, seccion: str, enfoque:str) -> str:
    all_res = "\n\n".join(
        f"{r['resumen']}\n{r['bibtex'] or ''}"
        for r in resumenes
    )
    task_write = Task(
        description=(
            f"Redacta una sección del {capitulo} en LaTeX sobre {seccion} enfocado en {enfoque}"
            "utilizando los siguientes resúmenes académicos y sus respectivas claves BibTeX. "
             "Cada resumen pertenece a un artículo diferente, y debe integrarse de forma fluida en el texto."
            "Asegúrate de citar correctamente usando \\cite{{clave}}.\n\nResúmenes y claves BibTeX:\n"
            "No incluyas la bibliografía completa, solo las citas dentro del texto."
            "\n\nResúmenes y claves BibTeX:\n" + all_res
        ),
        expected_output="Sección redactada en LaTeX con citas bien ubicadas.",
        agent=redactor,
    )
    return str(Crew(agents=[redactor], tasks=[task_write], verbose=True).kickoff())






def guardar_resultados(resumenes: list, texto_final: str):
    with open("resumenes_articulos.txt", "w", encoding="utf-8") as f:
        for r in resumenes:
            f.write(f"=== {r['archivo']} ===\n")
            f.write("Metadatos:\n" + r['metadata'] + "\n\n")
            f.write("Resumen:\n" + r['resumen'] + "\n\n")
            f.write("BibTeX:\n" + (r['bibtex'] or "No disponible") + "\n")
            f.write("="*80 + "\n\n")

    with open("referencias.bib", "a", encoding="utf-8") as f_bib:
        for r in resumenes:
            if r['bibtex']:
                f_bib.write(r['bibtex'] + "\n\n")

    with open("articulo_final.txt", "w", encoding="utf-8") as f_final:
        f_final.write(texto_final)




if __name__ == "__main__":
    carpeta = "Articulos_de_Prueba"
    enfoque = "Formas de resolver problemas de Scheduling timetabling"
    capitulo = "Estado del Arte"
    seccion_capitulo = "Scheduling Timetabling"

    resumenes = procesar_articulos(carpeta, enfoque, seccion_capitulo)
    subseccion = generar_capitulo(resumenes, capitulo, seccion_capitulo,enfoque)
    guardar_resultados(resumenes, subseccion)

    print("\n📘 Estado del arte generado:\n")
    print(subseccion)