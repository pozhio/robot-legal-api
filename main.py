import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
import uvicorn
import google.generativeai as genai
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 1. CEREBRO DE INTELIGENCIA ARTIFICIAL
# ==========================================

# Configurar la llave de Gemini (Render se la dará automáticamente)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

class DocumentoRequest(BaseModel):
    texto_documento: str
    pregunta: str

@app.post("/analizar-documento")
async def analizar_documento(req: DocumentoRequest):
    print(f"Recibiendo documento para analizar. Pregunta: {req.pregunta}")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt_estricto = f"""
        Eres un asistente legal experto y estricto de la plataforma Lex Compliance de México. 
        Tu ÚNICA tarea es responder a la pregunta del usuario utilizando EXCLUSIVAMENTE el documento proporcionado abajo. 
        
        REGLAS INQUEBRANTABLES:
        1. NO uses conocimiento externo a este documento.
        2. NO inventes información, artículos o leyes.
        3. Si la respuesta NO está claramente explicada en el texto del documento, debes responder EXACTAMENTE: "La información solicitada no se encuentra en el documento proporcionado."
        
        --- INICIO DEL DOCUMENTO ---
        {req.texto_documento}
        --- FIN DEL DOCUMENTO ---
        
        PREGUNTA DEL USUARIO:
        {req.pregunta}
        """
        
        response = model.generate_content(prompt_estricto)
        return {"respuesta": response.text}

    except Exception as e:
        print(f"Error en IA: {e}")
        return {"error": str(e)}

# ==========================================
# 2. BUSCADOR DE LA SCJN (El que ya tenías)
# ==========================================

async def buscar_scjn(query: str):
    print(f"Iniciando busqueda para: {query}")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            await page.route("**/*.{png,jpg,jpeg,css,woff,woff2,svg}", lambda route: route.abort())

            resultados = []
            url = f"https://bj.scjn.gob.mx/busqueda?q={query}"
            print(f"Navegando a: {url}")
            
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)
            
            tarjetas = await page.locator("mat-card, app-item-tesis, .mat-card, .card").all()
            
            if len(tarjetas) == 0:
                texto_pagina = await page.inner_text("body")
                return [{
                    "id": "debug",
                    "titulo": "⚠️ La SCJN está tardando demasiado en cargar",
                    "contenido": f"El robot esperó pero las tarjetas no se pintaron a tiempo. Lo que vio fue:\n\n{texto_pagina[:800]}...",
                    "fuente": "Sistema Debug",
                    "url": url
                }]

            for i, card in enumerate(tarjetas[:6]):
                texto = await card.inner_text()
                lines = texto.split('\n')
                
                titulo = "Resultado de la SCJN"
                for line in lines:
                    if len(line) > 15 and line.isupper():
                        titulo = line
                        break
                    elif len(line) > 10:
                        titulo = line
                        break
                
                try:
                    btn = card.locator("text=Ver extractos")
                    if await btn.count() > 0:
                        await btn.click(timeout=2000)
                        await page.wait_for_timeout(1000)
                        texto = await card.inner_text()
                except:
                    pass

                resultados.append({
                    "id": f"scjn-{i}",
                    "titulo": titulo[:250],
                    "contenido": texto[:1500],
                    "fuente": "SCJN",
                    "url": url
                })

            await browser.close()
            return resultados

    except Exception as e:
        return [{"id": "error", "titulo": "Error técnico", "contenido": str(e), "fuente": "Sistema", "url": "#"}]

@app.get("/buscar")
async def api_buscar(q: str):
    data = await buscar_scjn(q)
    return {"resultados": data}
