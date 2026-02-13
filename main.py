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
    print(f"Iniciando busqueda para: {query}") # Log para debug
    
    # --- CORRECCIÓN CRÍTICA: Mover el try afuera para capturar error de inicio ---
    try:
        async with async_playwright() as p:
            # --- CORRECCIÓN: Agregar argumentos anti-crash para servidor ---
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Bloqueamos recursos pesados
            await page.route("**/*.{png,jpg,jpeg,css,woff,woff2,svg}", lambda route: route.abort())

            resultados = []
            
            url = f"https://bj.scjn.gob.mx/busqueda?q={query}"
            print(f"Navegando a: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Esperar carga visual (máximo 10s)
            try:
                await page.wait_for_selector(".card, .mat-card", timeout=10000)
            except:
                print("Tiempo de espera visual agotado, intentando leer lo que haya.")

            # Extraer tarjetas
            tarjetas = await page.locator("app-item-tesis, .mat-card").all()
            print(f"Tarjetas encontradas: {len(tarjetas)}")
            
            for i, card in enumerate(tarjetas[:6]):
                texto = await card.inner_text()
                lines = texto.split('\n')
                titulo = lines[0] if len(lines) > 0 else "Resultado"
                
                # Intentar clic en "Ver extractos"
                try:
                    btn = card.locator("text=Ver extractos")
                    if await btn.count() > 0:
                        await btn.click(timeout=2000)
                        await page.wait_for_timeout(500) # Pequeña pausa
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
        # Devolvemos un error "bonito" en JSON en lugar de romper el servidor
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
