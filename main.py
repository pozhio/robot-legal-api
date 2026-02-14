import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            
            # Bloqueamos recursos pesados para acelerar
            await page.route("**/*.{png,jpg,jpeg,css,woff,woff2,svg}", lambda route: route.abort())

            resultados = []
            
            url = f"https://bj.scjn.gob.mx/busqueda?q={query}"
            print(f"Navegando a: {url}")
            
            # Aumentamos el tiempo general de carga
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # AUMENTAMOS LA PACIENCIA DEL ROBOT A 20 SEGUNDOS (Render es lento)
            try:
                await page.wait_for_selector(".card, .mat-card", timeout=20000)
            except:
                print("Tiempo visual agotado. Intentando leer de todas formas.")

            tarjetas = await page.locator("app-item-tesis, .mat-card").all()
            print(f"Tarjetas encontradas: {len(tarjetas)}")
            
            # --- EL TRUCO DE LOS OJOS (Si no hay resultados, vemos qué bloquea) ---
            if len(tarjetas) == 0:
                texto_pagina = await page.inner_text("body")
                return [{
                    "id": "debug",
                    "titulo": "⚠️ Diagnóstico del Robot (Página sin resultados o lenta)",
                    "contenido": f"El robot no encontró tarjetas. Esto es lo que vio en la página:\n\n{texto_pagina[:800]}...",
                    "fuente": "Sistema Debug",
                    "url": url
                }]
            # -----------------------------------------------------------------------

            for i, card in enumerate(tarjetas[:6]):
                texto = await card.inner_text()
                lines = texto.split('\n')
                titulo = lines[0] if len(lines) > 0 else "Resultado"
                
                try:
                    btn = card.locator("text=Ver extractos")
                    if await btn.count() > 0:
                        await btn.click(timeout=2000)
                        await page.wait_for_timeout(500)
                        texto = await card.inner_text()
                except:
                    pass

                resultados.append({
                    "id": f"cloud-{i}",
                    "titulo": titulo[:250],
                    "contenido": texto[:1500],
                    "fuente": "SCJN",
                    "url": url
                })

            await browser.close()
            return resultados

    except Exception as e:
        print(f"ERROR CRÍTICO: {e}")
        return [{
            "id": "error", 
            "titulo": "Error técnico en el servidor", 
            "contenido": f"Detalles: {str(e)}", 
            "fuente": "Sistema", 
            "url": "#"
        }]

@app.get("/buscar")
async def api_buscar(q: str):
    data = await buscar_scjn(q)
    return {"resultados": data}
