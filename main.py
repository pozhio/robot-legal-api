import os
from fastapi import FastAPI, HTTPException
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
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Importante: Usamos un User Agent común para no parecer robot
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        page = await context.new_page()
        
        # Bloqueamos imágenes para velocidad extrema
        await page.route("**/*.{png,jpg,jpeg,css,woff,woff2}", lambda route: route.abort())

        resultados = []
        try:
            url = f"https://bj.scjn.gob.mx/busqueda?q={query}"
            await page.goto(url, wait_until="domcontentloaded")
            
            # Esperar un poco a que cargue
            try:
                await page.wait_for_selector(".card, .mat-card", timeout=8000)
            except:
                pass

            # Extraer datos
            tarjetas = await page.locator("app-item-tesis, .mat-card").all()
            
            for i, card in enumerate(tarjetas[:6]):
                texto = await card.inner_text()
                lines = texto.split('\n')
                titulo = lines[0] if len(lines) > 0 else "Resultado"
                
                # Intentar clic en "Ver extractos"
                try:
                    btn = card.locator("text=Ver extractos")
                    if await btn.count() > 0:
                        await btn.click(timeout=1000)
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

        except Exception as e:
            print(f"Error: {e}")
            resultados.append({"id": "err", "titulo": "Error", "contenido": str(e), "fuente": "Sys", "url": "#"})
        finally:
            await browser.close()
    
    return resultados

@app.get("/buscar")
async def api_buscar(q: str):
    return {"resultados": await buscar_scjn(q)}
