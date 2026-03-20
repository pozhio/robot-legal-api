import os
import io
import gc # NUEVA LIBRERÍA: El Triturador Digital
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import PyPDF2
import docx
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

async def extraer_texto_archivo(file: UploadFile):
    contenido = await file.read()
    texto = ""
    try:
        if file.filename.lower().endswith('.pdf'):
            lector_pdf = PyPDF2.PdfReader(io.BytesIO(contenido))
            for pagina in lector_pdf.pages:
                if pagina.extract_text():
                    texto += pagina.extract_text() + "\n"
        elif file.filename.lower().endswith('.docx'):
            documento = docx.Document(io.BytesIO(contenido))
            for parrafo in documento.paragraphs:
                texto += parrafo.text + "\n"
        else:
            texto = contenido.decode('utf-8')
        return texto
    except Exception as e:
        raise Exception(f"No se pudo leer {file.filename}: {str(e)}")

@app.post("/analizar-documento")
async def analizar_documento(archivos: List[UploadFile] = File(...), pregunta: str = Form(...)):
    print(f"Analizando {len(archivos)} archivos de forma segura.")
    try:
        texto_total_documentos = ""
        
        for archivo in archivos:
            texto_extraido = await extraer_texto_archivo(archivo)
            texto_total_documentos += f"\n\n--- INICIO DEL DOCUMENTO: {archivo.filename} ---\n{texto_extraido}\n--- FIN DEL DOCUMENTO: {archivo.filename} ---\n"
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt_estricto = f"""
        Eres un asistente legal experto de Lex Compliance de México. 
        Responde ÚNICAMENTE usando los documentos proporcionados. Si la respuesta no está, di: "La información no se encuentra en los documentos." Menciona siempre la fuente.
        
        DOCUMENTOS:
        {texto_total_documentos}
        
        PREGUNTA:
        {pregunta}
        """
        
        response = model.generate_content(prompt_estricto)
        respuesta_final = response.text

        # ==========================================
        # EL TRITURADOR DIGITAL (BLINDAJE DE MEMORIA)
        # ==========================================
        texto_total_documentos = ""
        prompt_estricto = ""
        texto_extraido = ""
        del texto_total_documentos
        del prompt_estricto
        del texto_extraido
        del archivos
        gc.collect() # Fuerza la limpieza inmediata de la RAM
        # ==========================================

        return {"respuesta": respuesta_final}

    except Exception as e:
        print(f"Error en IA: {e}")
        return {"error": str(e)}
