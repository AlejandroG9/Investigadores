# Investigadores Project

## Project Overview

The Investigadores project is a comprehensive tool designed to facilitate the processing and analysis of scientific articles. This project aims to streamline the workflow associated with academic research by providing the following functionalities:

- **PDF Text Extraction:** Efficiently extracts and processes text from scientific articles in PDF format using multiple libraries like PyMuPDF, PyPDF2, and pdfminer.
- **Metadata Extraction:** Automatically identifies and extracts key metadata such as the title, authors, publication year, journal name, and DOI of the articles.
- **Summary Generation:** Uses artificial intelligence to generate structured summaries in LaTeX format, focusing on maintaining rigor and clarity required in academic contexts.
- **Integration of AI Models:** Leverages the power of OpenAI models to enhance the capability of processing and generating insightful summaries from complex scientific content.

By automating key aspects of article processing, the Investigadores project empowers researchers to focus more on analysis and interpretation, enhancing their productivity and the overall research experience.

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/AlejandroG9/Investigadores.git
   cd Investigadores
   ```

2. **Install dependencies:**
   Ensure you have Python and pip installed. Then, run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Environment Variables:**
   Ensure your OpenAI API key is set as an environment variable:
   ```bash
   export OPENAI_API_KEY=your_actual_api_key_here
   ```

## Detailed Explanation of `Equipo-Version-3.py`

`Equipo-Version-3.py` is a core script that integrates multiple agents for processing PDF documents. It includes:

- **OpenAI Integration:** Utilizes the `OpenAI` API via `langchain_openai` for language model tasks.
- **Agents Defined:** Three main agents are used:
  - `metadatos_agent`: Extracts metadata such as title, authors, and DOI.
  - `resumidor`: Generates structured scientific summaries in LaTeX format.
  - `redactor`: Compiles the state of the art sections using processed summaries.
- **PDF Processing Pipelines:** Employs libraries like `fitz` (PyMuPDF), `PyPDF2`, and `pdfminer` to extract and process text from PDF files.

## Dependencies

- Python 3.x
- Packages specified in `requirements.txt`, including `langchain_openai`, `fitz`, `requests`, etc.

## How to Run the Project

After setting up the project and dependencies, run the `Equipo-Version-3.py` script:
```bash
python Equipo-Version-3.py
```
This script will process PDFs in the specified directory, extracting metadata, generating summaries, and compiling an academic state-of-the-art document.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

