# Anthropic Daily

Web que muestra las 2 noticias más relevantes sobre Anthropic cada día, resumidas automáticamente con DeepSeek.

## Requisitos

- Python 3.10+
- pip

## Instalación

```bash
pip install fastapi uvicorn httpx
```

## Configuración

Establece tus claves de API como variables de entorno:

```bash
export DEEPSEEK_API_KEY="tu-clave-deepseek"
export SERPAPI_API_KEY="tu-clave-serpapi"
```

## Arrancar el servidor

```bash
python api_server.py
```

El servidor arranca en `http://localhost:8000`. Abre `index.html` en tu navegador o sirve los archivos estáticos con cualquier servidor web.

## Despliegue en producción

### Opción 1: Railway.app (gratis)

1. Crea una cuenta en [railway.app](https://railway.app)
2. Sube el proyecto o conecta tu repositorio de GitHub
3. Añade la variable de entorno `DEEPSEEK_API_KEY`
4. Railway detectará el servidor Python automáticamente

### Opción 2: VPS (Hetzner, OVH, etc.)

1. Sube los archivos al servidor
2. Instala dependencias: `pip install fastapi uvicorn httpx`
3. Configura la variable de entorno `DEEPSEEK_API_KEY`
4. Arranca con: `uvicorn api_server:app --host 0.0.0.0 --port 8000`
5. Usa nginx como proxy inverso para servir los archivos estáticos y redirigir `/api/*` al puerto 8000

### Opción 3: Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install fastapi uvicorn httpx
ENV DEEPSEEK_API_KEY=""
EXPOSE 8000
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Estructura

```
anthropic-news/
├── api_server.py   ← Backend (FastAPI + DeepSeek)
├── index.html      ← Página principal
├── base.css        ← Estilos base
├── style.css       ← Diseño y tokens
├── app.js          ← Lógica del frontend
└── README.md       ← Este archivo
```

## Notas

- Las noticias se buscan con SerpAPI (Google News) y se resumen con DeepSeek
- Si SerpAPI falla, usa Google News RSS como fallback
- Se cachean por hora para minimizar llamadas a la API
- El contador de visitas es en memoria (se reinicia con el servidor)
- Selector de idioma ES/EN en la cabecera
- Modo claro/oscuro

## Coste

~0.0003$ por petición a DeepSeek. Uso personal: menos de 0.10$/mes.
