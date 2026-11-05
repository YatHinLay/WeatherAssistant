"""Open-Meteo 地点搜索与天气工具，不生成或伪造气象数据。"""
import httpx
from langchain.tools import tool
from pydantic import BaseModel, Field

class City(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    country: str = Field(default='', max_length=100)
    region: str = Field(default='', max_length=100)

# 常用城市支持直接中文查询；其他城市交给地理编码服务。
CITIES = [City(name=n, latitude=a, longitude=o, country='中国') for n,a,o in [
    ('北京',39.9042,116.4074), ('上海',31.2304,121.4737),
    ('广州',23.1291,113.2644), ('深圳',22.5431,114.0579),
    ('杭州',30.2741,120.1551), ('成都',30.5728,104.0668),
    ('武汉',30.5928,114.3055), ('西安',34.3416,108.9398),
    ('南京',32.0603,118.7969), ('重庆',29.5630,106.5516),
    ('苏州',31.2989,120.5853), ('长沙',28.2282,112.9388),
    ('郑州',34.7466,113.6254), ('天津',39.3434,117.3616),
    ('青岛',36.0671,120.3826), ('厦门',24.4798,118.0894)
]]

def describe(code: int) -> str:
    if code == 0: return '晴'
    if code in (1, 2): return '少云'
    if code == 3: return '多云'
    if code in (45, 48): return '雾'
    if code in (51, 53, 55, 56, 57): return '毛毛雨'
    if code in (61, 63, 65, 66, 67, 80, 81, 82): return '雨'
    if code in (71, 73, 75, 77, 85, 86): return '雪'
    if code in (95, 96, 99): return '雷雨'
    return '未知天气'

async def search_cities(query: str) -> list[City]:
    local = [c for c in CITIES if query.removesuffix('市') in c.name]
    if local: return local
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get('https://geocoding-api.open-meteo.com/v1/search',
            params={'name':query,'count':6,'language':'zh','format':'json'})
        response.raise_for_status()
        return [City(name=r['name'], latitude=r['latitude'], longitude=r['longitude'],
            country=r.get('country',''), region=r.get('admin1',''))
            for r in response.json().get('results',[])]

async def reverse_city(city: City) -> City:
    async with httpx.AsyncClient(timeout=8) as client:
        response = await client.get('https://nominatim.openstreetmap.org/reverse',
            params={'lat':city.latitude, 'lon':city.longitude, 'format':'jsonv2',
                    'zoom':10, 'accept-language':'zh-CN'},
            headers={'User-Agent':'WeatherAssistant/1.0 (local weather app)'})
        response.raise_for_status()
        address = response.json().get('address', {})
    name = next((address.get(key) for key in ('city','town','municipality','village','county') if address.get(key)), None)
    if not name:
        raise ValueError('No city found for coordinates')
    return city.model_copy(update={'name':name, 'country':address.get('country',''),
        'region':' · '.join(dict.fromkeys(filter(None, [address.get('state'), name])))})

async def fetch_forecast(city: City) -> dict:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get('https://api.open-meteo.com/v1/forecast', params={
            'latitude':city.latitude, 'longitude':city.longitude, 'timezone':'auto',
            'current':'temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,is_day',
            'daily':'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max,uv_index_max',
            'forecast_days':7,
        })
        response.raise_for_status()
        data = response.json()
    current = data['current']
    daily = data['daily']
    if any(current.get(key) is None for key in ('time','temperature_2m','weather_code')):
        raise ValueError('Missing current weather')
    if any(v is None for key in ('temperature_2m_max','temperature_2m_min','weather_code') for v in daily[key]):
        raise ValueError('Missing forecast values')
    days = [dict(date=date, code=daily['weather_code'][i],
        description=describe(daily['weather_code'][i]),
        high=daily['temperature_2m_max'][i], low=daily['temperature_2m_min'][i],
        rain=daily['precipitation_probability_max'][i],
        wind=daily['wind_speed_10m_max'][i], uv=daily['uv_index_max'][i])
        for i,date in enumerate(daily['time'])]
    return dict(city=city.model_dump(), timezone=data['timezone'],
        current=dict(time=current['time'], temperature=current['temperature_2m'],
            apparent=current['apparent_temperature'], humidity=current['relative_humidity_2m'],
            wind=current['wind_speed_10m'], code=current['weather_code'],
            description=describe(current['weather_code']), is_day=current['is_day']),
        days=days, source='Open-Meteo', source_url='https://open-meteo.com/')

@tool
async def query_weather(city: City) -> dict:
    """查询指定城市的实时天气及未来七日预报，温度单位摄氏度、风速单位 km/h。"""
    return await fetch_forecast(city)
