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
            
            # Bloqueamos recursos pesados para velocidad
            await page.route("**/*.{png,jpg,jpeg,css,woff,woff2,svg}", lambda route: route.abort())

            resultados = []
            url = f"https://bj.scjn.gob.mx/busqueda?q={query}"
            print(f"Navegando a: {url}")
            
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # --- LA SOLUCIÓN: PAUSA OBLIGATORIA DE 5 SEGUNDOS ---
            # Dejamos que Angular termine de traer las sentencias de la base de datos
            await page.wait_for_timeout(5000)
            
            # Buscamos con selectores amplios por si cambiaron el código de la SCJN
            tarjetas = await page.locator("mat-card, app-item-tesis, .mat-card, .card").all()
            print(f"Tarjetas encontradas: {len(tarjetas)}")
            
            # El diagnóstico (por si acaso)
            if len(tarjetas) == 0:
                texto_pagina = await page.inner_text("body")
                return [{
                    "id": "debug",
                    "titulo": "⚠️ La SCJN está tardando demasiado en cargar",
                    "contenido": f"El robot esperó pero las tarjetas no se pintaron a tiempo. Lo que vio fue:\n\n{texto_pagina[:800]}...",
                    "fuente": "Sistema Debug",
                    "url": url
                }]

            # Extraemos la información
            for i, card in enumerate(tarjetas[:6]):
                texto = await card.inner_text()
                lines = texto.split('\n')
                
                # Intentamos buscar un título razonable
                titulo = "Resultado de la SCJN"
                for line in lines:
                    if len(line) > 15 and line.isupper():
                        titulo = line
                        break
                    elif len(line) > 10:
                        titulo = line
                        break
                
                # Clic en "Ver extractos"
                try:
                    btn = card.locator("text=Ver extractos")
                    if await btn.count() > 0:
                        await btn.click(timeout=2000)
                        await page.wait_for_timeout(1000) # Espera a que baje el texto
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
