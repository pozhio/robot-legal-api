import os
import io
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import google.generativeai as genai
import PyPDF2
import docx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# CEREBRO DE INTELIGENCIA ARTIFICIAL (IA LOCAL)
# ==========================================

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Función para extraer el texto de los archivos
async def extraer_texto_archivo(file: UploadFile):
    contenido = await file.read()
    texto = ""
    
    try:
        if file.filename.lower().endswith('.pdf'):
            lector_pdf = PyPDF2.PdfReader(io.BytesIO(contenido))
            for pagina in lector_pdf.pages:
                texto += pagina.extract_text() + "\n"
                
        elif file.filename.lower().endswith('.docx'):
            documento = docx.Document(io.BytesIO(contenido))
            for parrafo in documento.paragraphs:
                texto += parrafo.text + "\n"
        else:
            texto = contenido.decode('utf-8')
            
        return texto
    except Exception as e:
        raise Exception(f"No se pudo leer el archivo: {str(e)}")

@app.post("/analizar-documento")
async def analizar_documento(file: UploadFile = File(...), pregunta: str = Form(...)):
    print(f"Recibiendo archivo: {file.filename} para responder: {pregunta}")
    try:
        # Extraemos el texto del PDF o DOCX
        texto_documento = await extraer_texto_archivo(file)
        
        # Le pasamos el texto a la IA con las reglas estrictas
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt_estricto = f"""
        Eres un asistente legal experto y estricto de la plataforma Lex Compliance de México. 
        Tu ÚNICA tarea es responder a la pregunta del usuario utilizando EXCLUSIVAMENTE el documento proporcionado abajo. 
        
        REGLAS INQUEBRANTABLES:
        1. NO uses conocimiento externo a este documento bajo ninguna circunstancia.
        2. NO inventes información, artículos o leyes.
        3. Si la respuesta NO está claramente explicada en el texto del documento, debes responder EXACTAMENTE: "La información solicitada no se encuentra en el documento proporcionado."
        
        --- INICIO DEL DOCUMENTO ---
        {texto_documento}
        --- FIN DEL DOCUMENTO ---
        
        PREGUNTA DEL USUARIO:
        {pregunta}
        """
        
        response = model.generate_content(prompt_estricto)
        return {"respuesta": response.text}

    except Exception as e:
        print(f"Error en IA: {e}")
        return {"error": str(e)}
