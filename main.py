import os
import io
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
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

# AQUI ESTA LA MAGIA: Recibimos una lista de archivos
@app.post("/analizar-documento")
async def analizar_documento(archivos: List[UploadFile] = File(...), pregunta: str = Form(...)):
    print(f"Recibiendo {len(archivos)} archivos para responder: {pregunta}")
    try:
        texto_total_documentos = ""
        
        # Juntamos todos los textos separándolos por su nombre de archivo
        for archivo in archivos:
            texto_extraido = await extraer_texto_archivo(archivo)
            texto_total_documentos += f"\n\n--- INICIO DEL DOCUMENTO: {archivo.filename} ---\n"
            texto_total_documentos += texto_extraido
            texto_total_documentos += f"\n--- FIN DEL DOCUMENTO: {archivo.filename} ---\n"
        
        # Usamos el modelo más nuevo
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt_estricto = f"""
        Eres un asistente legal experto y estricto de la plataforma Lex Compliance de México. 
        Tu ÚNICA tarea es responder a la pregunta del usuario utilizando EXCLUSIVAMENTE los documentos proporcionados abajo. 
        
        REGLAS INQUEBRANTABLES:
        1. NO uses conocimiento externo bajo ninguna circunstancia.
        2. NO inventes información, artículos o leyes.
        3. Si la respuesta NO está en los documentos, responde EXACTAMENTE: "La información solicitada no se encuentra en los documentos proporcionados."
        4. Cuando respondas, menciona siempre de qué documento (nombre del archivo) sacaste la información.
        
        DOCUMENTOS DE REFERENCIA:
        {texto_total_documentos}
        
        PREGUNTA DEL USUARIO:
        {pregunta}
        """
        
        response = model.generate_content(prompt_estricto)
        return {"respuesta": response.text}

    except Exception as e:
        print(f"Error en IA: {e}")
        return {"error": str(e)}
