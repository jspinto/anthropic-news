#!/usr/bin/env python3
"""Backend server for Anthropic Daily — searches real news, then summarizes via DeepSeek API."""

import os
import json
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

import httpx
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY", "")

MESES = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December']

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# --- Step 1: Search for real Anthropic news ---

async def fetch_news_articles(client: httpx.AsyncClient) -> list[dict]:
    """Fetch recent Anthropic news articles via SerpAPI Google News."""
    articles = []

    try:
        resp = await client.get(
            "https://serpapi.com/search.json",
            params={
                "engine": "google_news",
                "q": "Anthropic AI",
                "gl": "us",
                "hl": "en",
                "api_key": SERPAPI_API_KEY,
            },
            timeout=20.0,
        )
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("news_results", [])[:8]:
            title = item.get("title", "")
            link = item.get("link", "")
            source = item.get("source", {}).get("name", "Unknown") if isinstance(item.get("source"), dict) else item.get("source", "Unknown")
            pub_date = item.get("date", "")

            if title:
                articles.append({
                    "title": title,
                    "url": link,
                    "source": source,
                    "date": pub_date,
                })
    except Exception as e:
        print(f"SerpAPI fetch error: {e}")

    # Fallback to Google News RSS if SerpAPI fails
    if not articles:
        try:
            rss_url = "https://news.google.com/rss/search?q=Anthropic+AI&hl=en&gl=US&ceid=US:en&when=1d"
            resp = await client.get(rss_url, timeout=15.0, follow_redirects=True)
            resp.raise_for_status()
            items = re.findall(r'<item>(.*?)</item>', resp.text, re.DOTALL)
            for item in items[:8]:
                title_m = re.search(r'<title>(.*?)</title>', item)
                link_m = re.search(r'<link/>\s*(https?://[^\s<]+)', item)
                source_m = re.search(r'<source[^>]*>(.*?)</source>', item)
                title = (title_m.group(1) if title_m else "").replace("&amp;", "&").replace("&#39;", "'")
                if title:
                    articles.append({
                        "title": title,
                        "url": link_m.group(1) if link_m else "",
                        "source": (source_m.group(1) if source_m else "Unknown").replace("&amp;", "&"),
                        "date": "",
                    })
        except Exception as e:
            print(f"RSS fallback error: {e}")

    return articles


# --- Step 2: Send articles to DeepSeek for summarization ---

async def summarize_with_deepseek(client: httpx.AsyncClient, articles: list[dict], lang: str = "es") -> dict:
    """Send real news articles to DeepSeek and get 2 summarized stories."""

    now_utc = datetime.now(timezone.utc)
    if lang == "es":
        today = f"{now_utc.day} de {MESES[now_utc.month - 1]} de {now_utc.year}"
    else:
        today = f"{MONTHS[now_utc.month - 1]} {now_utc.day}, {now_utc.year}"

    # Build article context for DeepSeek
    articles_text = "\n\n".join([
        f"[{i+1}] {a['title']}\n    Fuente/Source: {a['source']}\n    URL: {a['url']}\n    Fecha/Date: {a['date']}"
        for i, a in enumerate(articles)
    ])

    if lang == "es":
        prompt = f"""Hoy es {today}. A continuación tienes una lista de artículos reales de noticias sobre Anthropic encontrados hoy en Internet:

{articles_text}

Tu tarea:
1. Selecciona las 2 noticias más relevantes e interesantes de la lista anterior.
2. Para cada noticia, escribe:
   - Un titular breve y llamativo en español
   - Un resumen de 2-3 frases en español basándote en el título del artículo original
   - La fuente original (nombre del medio) y la URL exacta del artículo
3. Crea un titular general del día que englobe ambas noticias.

IMPORTANTE: Usa SOLO la información de los artículos proporcionados. No inventes noticias.

Responde EXCLUSIVAMENTE en formato JSON válido, sin markdown ni backticks:
{{
  "titular_del_dia": "string",
  "fecha": "{today}",
  "noticias": [
    {{
      "titular": "string",
      "resumen": "string",
      "fuente": "string",
      "url": "string"
    }},
    {{
      "titular": "string",
      "resumen": "string",
      "fuente": "string",
      "url": "string"
    }}
  ]
}}"""
    else:
        prompt = f"""Today is {today}. Below is a list of real news articles about Anthropic found today on the Internet:

{articles_text}

Your task:
1. Select the 2 most relevant and interesting news stories from the list above.
2. For each story, write:
   - A short, catchy headline in English
   - A 2-3 sentence summary in English based on the original article title
   - The original source (media name) and exact article URL
3. Create a general headline of the day that encompasses both stories.

IMPORTANT: Use ONLY information from the articles provided. Do not invent news.

Respond EXCLUSIVELY in valid JSON format, without markdown or backticks:
{{
  "titular_del_dia": "string",
  "fecha": "{today}",
  "noticias": [
    {{
      "titular": "string",
      "resumen": "string",
      "fuente": "string",
      "url": "string"
    }},
    {{
      "titular": "string",
      "resumen": "string",
      "fuente": "string",
      "url": "string"
    }}
  ]
}}"""

    system_msg = (
        "You are an assistant that responds exclusively in valid JSON. Do not use markdown, backticks or additional text."
        if lang == "en" else
        "Eres un asistente que responde exclusivamente en JSON válido. No uses markdown, backticks ni texto adicional."
    )

    response = await client.post(
        f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 1024,
        },
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"].strip()

    # Clean potential markdown wrapping
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

    return json.loads(content)


# --- Cache per language ---
_cache = {
    "es": {"data": None, "hour": None},
    "en": {"data": None, "hour": None},
}

# --- Visit counter ---
_visit_count = 0


@app.get("/api/news")
async def get_news(lang: str = "es"):
    """Return today's Anthropic news, cached per hour per language."""
    if lang not in ("es", "en"):
        lang = "es"

    now = datetime.now(timezone.utc)
    current_hour = now.strftime("%Y-%m-%d-%H")

    if _cache[lang]["data"] and _cache[lang]["hour"] == current_hour:
        return _cache[lang]["data"]

    try:
        async with httpx.AsyncClient() as client:
            # Step 1: Fetch real news from the web
            articles = await fetch_news_articles(client)

            if not articles:
                fecha = f"{now.day} de {MESES[now.month - 1]} de {now.year}" if lang == "es" else f"{MONTHS[now.month - 1]} {now.day}, {now.year}"
                return {
                    "titular_del_dia": "No se encontraron noticias" if lang == "es" else "No news found",
                    "fecha": fecha,
                    "noticias": [],
                }

            # Step 2: Summarize with DeepSeek
            result = await summarize_with_deepseek(client, articles, lang)
            _cache[lang]["data"] = result
            _cache[lang]["hour"] = current_hour
            return result

    except Exception as e:
        if _cache[lang]["data"]:
            return _cache[lang]["data"]
        fecha = f"{now.day} de {MESES[now.month - 1]} de {now.year}" if lang == "es" else f"{MONTHS[now.month - 1]} {now.day}, {now.year}"
        return {
            "titular_del_dia": "No se pudieron obtener noticias" if lang == "es" else "Could not fetch news",
            "fecha": fecha,
            "noticias": [],
            "error": str(e),
        }


@app.get("/api/visits")
async def visits():
    """Increment and return visit count."""
    global _visit_count
    _visit_count += 1
    return {"count": _visit_count}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# --- Serve static frontend files ---
STATIC_DIR = Path(__file__).parent

@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")

app.mount("/", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
