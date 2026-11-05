from pathlib import Path
import logging
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).parents[1] / '.env')
from .graph import graph
from .weather import City, search_cities, fetch_forecast, reverse_city

app = FastAPI(title='WeatherAssistant', version='1.0.0')
app.add_middleware(CORSMiddleware,
    allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],
    allow_methods=['GET','POST'], allow_headers=['Content-Type'])
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    city: City | None = None

class ChatResponse(BaseModel):
    reply: str
    city: City | None = None
    weather: dict | None = None
    mode: str = 'rules'
    trace: list[str]

@app.get('/api/health')
def health():
    return {'status':'ok'}

@app.get('/api/cities', response_model=list[City])
async def cities(q: str = Query(min_length=1,max_length=100)):
    try:
        return await search_cities(q.strip())
    except httpx.HTTPError as exc:
        raise HTTPException(502,'城市服务暂时不可用，请稍后重试。') from exc

@app.post('/api/location', response_model=City)
async def location(city: City):
    try:
        return await reverse_city(city)
    except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
        raise HTTPException(502,'城市名称暂时无法获取，仍按定位坐标查询天气。') from exc

@app.post('/api/weather')
async def weather(city: City):
    """独立天气查询，不调用问答图或模型。"""
    try:
        return await fetch_forecast(city)
    except httpx.HTTPError as exc:
        raise HTTPException(502,'天气服务连接失败，请稍后重试。') from exc
    except (KeyError, ValueError, TypeError) as exc:
        logger.exception('天气服务返回了无法解析的数据')
        raise HTTPException(502,'天气数据暂时不完整，请稍后重试。') from exc

@app.post('/api/chat', response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(422,'请输入问题。')
    try:
        result = await graph.ainvoke(dict(message=request.message.strip(),
            city=request.city.model_dump() if request.city else None))
        return ChatResponse(**{k:v for k,v in result.items() if k in ChatResponse.model_fields})
    except httpx.HTTPError as exc:
        raise HTTPException(502,'天气服务连接失败，请稍后重试；当前不会显示模拟天气。') from exc
    except (KeyError, ValueError, TypeError) as exc:
        logger.exception('天气服务返回了无法解析的数据')
        raise HTTPException(502,'天气数据暂时不完整，请稍后重试。') from exc

dist = Path(__file__).parents[2] / 'frontend' / 'dist'
if dist.exists():
    app.mount('/', StaticFiles(directory=dist,html=True),name='frontend')
