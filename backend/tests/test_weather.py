import unittest
from unittest.mock import AsyncMock, patch
import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.weather import CITIES, City, reverse_city
import asyncio

WEATHER = dict(city=CITIES[0].model_dump(), timezone='Asia/Shanghai',
    current=dict(time='2026-11-05T10:00',temperature=18,apparent=17,humidity=40,wind=8,code=0,description='晴',is_day=1),
    days=[dict(date=f'2026-11-0{i+5}',code=61,description='雨',high=22,low=12,rain=80,wind=15,uv=3) for i in range(3)],
    source='Open-Meteo',source_url='https://open-meteo.com/')

class WeatherTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.env = patch.dict('os.environ',{'OPENAI_API_KEY':'','WEATHER_MODEL':''})
        self.env.start()
        self.addCleanup(self.env.stop)

    @patch('app.weather.fetch_forecast',new_callable=AsyncMock,return_value=WEATHER)
    def test_graph_tool_and_followup(self,fetch):
        response = self.client.post('/api/chat',json={'message':'明天要带伞吗？','city':CITIES[0].model_dump()})
        self.assertEqual(response.status_code,200)
        data = response.json()
        self.assertIn('2026-11-06',data['reply'])
        self.assertIn('带伞',data['reply'])
        self.assertEqual(len(data['trace']),3)
        fetch.assert_awaited_once()

    def test_missing_city_does_not_fetch(self):
        data = self.client.post('/api/chat',json={'message':'明天会下雨吗'}).json()
        self.assertIsNone(data['weather'])
        self.assertIn('城市',data['reply'])

    @patch('app.graph.search_cities',new_callable=AsyncMock)
    @patch('app.weather.fetch_forecast',new_callable=AsyncMock,return_value=WEATHER)
    def test_assistant_help_uses_knowledge_without_weather_requests(self,fetch,search):
        for message in ('你能干什么','你能干啥','你能干嘛？','你能做啥','你有啥功能','你有哪些功能？','你好','怎么使用天气助手'):
            for city in (None,CITIES[0].model_dump()):
                with self.subTest(message=message,city=city):
                    data = self.client.post('/api/chat',json={'message':message,'city':city}).json()
                    self.assertIn('天气',data['reply'])
                    self.assertNotIn('想了解哪个城市',data['reply'])
                    self.assertIsNone(data['weather'])
                    self.assertEqual(data['city'],city)
                    self.assertIn('检索使用说明',data['trace'])
        fetch.assert_not_awaited()
        search.assert_not_awaited()

    @patch('app.weather.fetch_forecast',new_callable=AsyncMock,return_value=WEATHER)
    def test_greeting_with_weather_question_still_fetches_weather(self,fetch):
        response = self.client.post('/api/chat',json={'message':'你好，北京明天要带伞吗？'})
        self.assertEqual(response.status_code,200)
        self.assertIn('2026-11-06',response.json()['reply'])
        fetch.assert_awaited_once()

    @patch('app.weather.fetch_forecast',new_callable=AsyncMock,side_effect=httpx.ConnectError('offline'))
    def test_network_error_is_not_fake_weather(self,fetch):
        response = self.client.post('/api/chat',json={'message':'北京天气'})
        self.assertEqual(response.status_code,502)

    @patch('app.main.graph.ainvoke',new_callable=AsyncMock)
    @patch('app.main.fetch_forecast',new_callable=AsyncMock,return_value=WEATHER)
    def test_search_does_not_invoke_assistant(self,fetch,chat):
        response = self.client.post('/api/weather',json=CITIES[0].model_dump())
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['city']['name'],'北京')
        fetch.assert_awaited_once()
        chat.assert_not_awaited()

    def test_input_validation(self):
        self.assertEqual(self.client.post('/api/chat',json={'message':''}).status_code,422)
        self.assertEqual(self.client.post('/api/chat',json={'message':'天气','city':{'name':'x','latitude':100,'longitude':1}}).status_code,422)

    @patch('app.weather.httpx.AsyncClient.get',new_callable=AsyncMock)
    def test_reverse_city_preserves_actual_coordinates(self,get):
        place = City(name='当前位置',latitude=31.23,longitude=121.47)
        for address in ({'city':'上海市','state':'上海市','country':'中国'}, {'town':'某镇'}):
            get.return_value = httpx.Response(200,json={'address':address},request=httpx.Request('GET','https://example.com'))
            resolved = asyncio.run(reverse_city(place))
            self.assertEqual(resolved.name, address.get('city') or address['town'])
            self.assertEqual((resolved.latitude,resolved.longitude),(31.23,121.47))
            self.assertEqual(resolved.region,resolved.name)

    @patch('app.main.reverse_city',new_callable=AsyncMock,side_effect=ValueError('No city'))
    def test_location_failure_is_explicit(self,reverse):
        response = self.client.post('/api/location',json=CITIES[0].model_dump())
        self.assertEqual(response.status_code,502)
        self.assertIn('城市名称暂时无法获取',response.json()['detail'])
        self.assertEqual(self.client.post('/api/location',json={'name':'当前位置','latitude':91,'longitude':0}).status_code,422)

    @patch('app.weather.fetch_forecast',new_callable=AsyncMock,return_value=WEATHER)
    @patch('app.graph.search_cities',new_callable=AsyncMock)
    def test_selected_district_keeps_coordinates(self,search,fetch):
        place = dict(name='朝阳区', latitude=39.92, longitude=116.43, country='中国', region='北京市')
        response = self.client.post('/api/chat',json={'message':'朝阳区今天天气怎么样？','city':place})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['city'],place)
        self.assertEqual(fetch.await_args.args[0].latitude,39.92)
        search.assert_not_awaited()

    def test_unsupported_date(self):
        data = self.client.post('/api/chat',json={'message':'北京下周天气'}).json()
        self.assertIsNone(data['weather'])
        self.assertIn('未来七日',data['reply'])

if __name__ == '__main__': unittest.main()
