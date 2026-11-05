# 晴语 · WeatherAssistant

FastAPI + LangChain + LangGraph + Vue 3 天气助手，默认无需 API Key。

## 启动

本机环境：Python 3.15，Node.js 26。安装完成后，双击根目录 `start-backend.cmd`，
打开 http://127.0.0.1:8000 即可使用已经构建的前端。
接口文档：http://127.0.0.1:8000/docs。

开发时另开终端运行 `start-frontend.cmd`，访问 http://127.0.0.1:5173。
前端开发服务器将 `/api` 代理到 8000，前后端需要同时运行。

PyCharm 打开本项目，解释器选择 `backend/.venv/Scripts/python.exe`。
运行模块 `uvicorn`，参数 `app.main:app --host 127.0.0.1 --port 8000`，工作目录设为 `backend`。

## 重新安装

```powershell
cd backend
$env:UV_CACHE_DIR="$PWD/.uv-cache"
uv sync --python 'D:/Program Files/Python315/python.exe' --frozen --link-mode copy
.venv/Scripts/python.exe -m unittest discover -s tests -v
cd ../frontend
npm.cmd ci
npm.cmd run build
```

## 可选模型接入

复制 `backend/.env.example` 为 `backend/.env`，设置 `WEATHER_MODEL`（模型名称）、
`OPENAI_API_KEY`、可选 `OPENAI_BASE_URL`，然后重启后端。
密钥只保存在后端。模型只读取本轮用户问题和所查城市的天气，不接收完整聊天记录。
不配置时使用规则回答；模型故障会回退规则回答并在界面提示。

## 设计

- `backend/app/weather.py`：Open-Meteo 城市搜索、真实气象 API、LangChain 天气工具。
- `backend/app/graph.py`：LangGraph 解析问题 → 调用 LangChain Tool → 生成建议。
- `backend/app/main.py`：FastAPI 请求校验、接口与前端静态托管。
- `frontend/src/App.vue`：城市选择、天气卡片、七日预报、聊天及查询过程。
- 城市上下文保存在页面内存并随请求传入，不保存个人聊天数据到数据库。
- 未配置模型时，聊天支持常用城市、形如“苏黎世天气”的地名查询、今天/明天/后天与当前城市追问。
  地名歧义时需使用城市搜索选择；其他日期需查看七日卡片。模型仅负责天气表达，不提供无限制的通用聊天。
- 天气请求失败显示错误，不使用模拟数据填充。页面展示地点和当地数据时间。

## 数据来源

Open-Meteo：https://open-meteo.com/ ，地理编码基于 GeoNames。
免费天气接口面向非商业使用；商业部署前请确认服务条款与相应套餐。
预报并非灾害预警，请以当地气象机构最新预警为准。
本项目默认仅绑定本机，不包含公网账号、鉴权与限流。

## 本机验证记录

- Python 3.15.2，依赖已安装；uv.lock 和 package-lock.json 已生成。
- 5 项自动检查通过：天气工具与追问、缺少城市、非法输入、天气网络故障、日期范围提示。
- 真实 Open-Meteo 请求及 /api/chat 查询成功，返回 7 日预报。
- Vue 生产构建成功；浏览器中已验证城市选择、实时天气卡片和同城追问。
- 未配置真实模型密钥，因此尚未验证可选模型服务调用。

## 省市区选择

热门城市下方提供省份→城市→区县三级联动。改变上级会清空下级，选择完成后点击“搜索天气”才发起查询。
直辖市在省份和城市两级均显示城市名称。区县中心坐标随请求传递，避免同名区县混淆。

数据来源：
- 区划名称及代码：https://github.com/modood/Administrative-divisions-of-China （2023 年数据，当前已停止更新，覆盖大陆 31 个省级地区）。
- 代表点坐标：https://github.com/pfinal/city （2020 年 BD-09 数据；scripts/prepare_regions.py 转换为近似 WGS-84，并仅按代码与名称同时匹配）。
- 本地数据共 3056 个区县条目，其中 2989 个匹配代表点坐标。其余条目显示“暂缺坐标”，可使用上方城市搜索；不会使用父级城市坐标冒充区县坐标。
- 区县天气对应代表点所在的预报网格，不代表区县每个位置的实测值。数据快照不等同于最新行政区划。

此次更新：6 项后端测试通过，前端构建通过；已在浏览器选择北京市→北京市→海淀区，点击搜索并成功显示天气及七日预报。

## 搜索与助手独立运行

能力介绍、问候、使用帮助和定位说明先从 `backend/app/knowledge.json` 检索，不要求提供城市，也不调用天气接口。检索按预设短语匹配并优先使用最长匹配；纯问候需完整匹配，避免拦截“你好，北京明天天气怎么样”。这是适用于小型说明库的关键词 RAG，无需向量数据库或额外依赖。配置模型后以检索片段生成回答；未配置、模型失败或返回空内容时直接返回知识库说明。新增说法和说明可在该 JSON 中维护。

天气卡片、热门城市和省市区搜索通过 `/api/weather` 查询，只更新页面天气，不写入对话，不调用大模型。
浮动问答助手通过 `/api/chat` 工作，拥有独立的城市上下文、加载状态与错误提示；在对话里输入城市开始查询，问答结果不会改变页面天气。
问答界面已移除“本次查询过程”。后端流程仍保留，用于内部编排。
验证：7 项自动检查通过，包含天气搜索不调用问答图的回归检查；前端生产构建通过。

## 浏览器定位

页面加载时通过 `navigator.geolocation.getCurrentPosition` 请求一次位置权限，允许后默认查询当前位置天气；可点击“定位当前位置”重试。开启高精度，15 秒超时，允许使用 60 秒内的缓存定位。
浏览器定位可能使用 GPS、Wi-Fi 或系统定位服务，电脑不一定配备 GPS。位置精度随设备和环境变化。
实际坐标传入 `/api/location`，由后端请求 Nominatim / OpenStreetMap 反向地理编码，天气卡片的定位详情行按“上海市 · Asia/Shanghai”格式显示城市名称和时区。该服务暂不可用时提示城市名称获取失败，仍查询坐标天气。
天气通过独立的 `/api/weather` 查询，再由后端请求 Open-Meteo；坐标不写入助手对话，也不写入本项目的持久化存储。城市名称来源：[© OpenStreetMap contributors](https://www.openstreetmap.org/copyright)，[反向地理编码接口文档](https://nominatim.org/release-docs/latest/api/Reverse/)。
未取得位置或拒绝权限时保留手动搜索；手动搜索或切换地区会使待返回的定位结果失效，避免覆盖手动选择。
定位需要 HTTPS 或 localhost/127.0.0.1 安全本机环境，普通 HTTP 局域网地址通常不可用。相关规范：https://developer.mozilla.org/en-US/docs/Web/API/Geolocation/getCurrentPosition

验证：`cd frontend; npm.cmd test` 的 4 项模拟定位检查及生产构建通过。未在测试中获取用户真实位置；实际设备定位需用户在浏览器授权。
