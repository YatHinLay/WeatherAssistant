<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { getCurrentLocation } from './geolocation.js'
import regions from './regions.json'
const city = ref(null), weather = ref(null), query = ref(''), results = ref([])
const searching = ref(false), busy = ref(false), input = ref(''), error = ref(''), searchError = ref(''), conversation = ref(null)
const mode = ref('rules'), chatCity = ref(null), weatherBusy = ref(false), weatherError = ref('')
const locating = ref(false), locationMessage = ref(''), locatedName = ref('')
let locationRequest = 0
function cancelLocation() { locationRequest++; locating.value = false; locationMessage.value = '' }
async function locate() {
  if (locating.value || weatherBusy.value) return
  const request = ++locationRequest
  locating.value = true; locationMessage.value = ''
  try {
    let place = await getCurrentLocation()
    let nameError = '', name = ''
    if (request !== locationRequest) return
    try {
      const resolved = await api('/location', place)
      name = resolved.name
      place = {...place, country:resolved.country, region:resolved.name}
    } catch {
      nameError = '城市名称暂时无法获取，仍按定位坐标查询天气。'
    }
    if (request !== locationRequest) return
    locatedName.value = name
    locating.value = false
    await choose(place)
    if (request + 1 === locationRequest) locationMessage.value = nameError
  } catch (e) {
    if (request === locationRequest) locationMessage.value = e.message
  } finally {
    if (request === locationRequest) locating.value = false
  }
}
onMounted(locate)
const chatOpen = ref(false), chatLauncher = ref(null), chatInput = ref(null)
async function toggleChat() {
  chatOpen.value = !chatOpen.value
  await nextTick()
  if (chatOpen.value) { await scroll(); chatInput.value?.focus() }
  else chatLauncher.value?.focus()
}
async function closeChat() {
  chatOpen.value = false
  await nextTick()
  chatLauncher.value?.focus()
}
const messages = ref([{role:'assistant',text:'你好，我是晴语。告诉我你想了解的城市，比如“北京明天天气怎么样？”'}])
const suggestions = ['明天需要带伞吗？','今天适合出门吗？','后天穿什么合适？']
const provinceCode = ref(''), cityCode = ref(''), districtCode = ref('')
const province = computed(() => regions.find(item => item.code === provinceCode.value))
const regionCities = computed(() => province.value?.children || [])
const regionCity = computed(() => regionCities.value.find(item => item.code === cityCode.value))
const districts = computed(() => regionCity.value?.children || [])
const district = computed(() => districts.value.find(item => item.code === districtCode.value))
function changeProvince() { cancelLocation(); cityCode.value = ''; districtCode.value = '' }
function changeCity() { cancelLocation(); districtCode.value = '' }
async function searchRegion() {
  if (!district.value || district.value.latitude == null || weatherBusy.value || searching.value) return
  await choose({name:district.value.name, latitude:district.value.latitude, longitude:district.value.longitude,
    country:'中国',region:[province.value.name,regionCity.value.name].filter((name,i,all) => all.indexOf(name) === i).join(' · ')})
}
const popular = ['北京','上海','广州','深圳','杭州','成都','重庆','武汉','南京','西安','长沙','苏州','天津','郑州','青岛','厦门']
function icon(code) { return code === 0 ? '☀' : code < 4 ? '☁' : code < 50 ? '≋' : code >= 95 ? '⛈' : [71,73,75,77,85,86].includes(code) ? '❄' : '☂' }
function dayLabel(date,i) { return i === 0 ? '今天' : i === 1 ? '明天' : new Date(date+'T12:00:00').toLocaleDateString('zh-CN',{weekday:'short'}) }
async function api(path, body) {
  const response = await fetch('/api'+path, body ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body), signal:AbortSignal.timeout(65000)} : {signal:AbortSignal.timeout(20000)})
  const data = await response.json()
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '请求未成功，请检查输入后重试。')
  return data
}
async function search(value = query.value) {
  if (!value.trim() || searching.value) return
  cancelLocation()
  query.value = value; searching.value = true; searchError.value = ''; results.value = []
  try { results.value = await api('/cities?q='+encodeURIComponent(value.trim())); if (!results.value.length) searchError.value = '没有找到城市，请尝试完整名称。' }
  catch (e) { searchError.value = e.name === 'TimeoutError' ? '搜索超时，请重试。' : e.message }
  finally { searching.value = false }
}
async function choosePopular(name) {
  if (weatherBusy.value || searching.value) return
  await search(name)
  const place = results.value.find(item => item.name === name)
  if (place) await choose(place)
}
async function choose(place) {
  if (weatherBusy.value) return
  cancelLocation()
  city.value = place; weather.value = null; results.value = []; query.value = ''
  weatherBusy.value = true; weatherError.value = ''
  try { weather.value = await api('/weather', place) }
  catch (e) { weatherError.value = e.name === 'TimeoutError' ? '查询超时，请稍后重试。' : e.message }
  finally { weatherBusy.value = false }
}
async function send(text = input.value) {
  if (!text.trim() || busy.value) return
  input.value = ''; busy.value = true; error.value = ''
  messages.value.push({role:'user',text})
  await scroll()
  try {
    const data = await api('/chat',{message:text,city:chatCity.value})
    messages.value.push({role:'assistant',text:data.reply})
    if (data.city) chatCity.value = data.city
    mode.value = data.mode
  } catch (e) { error.value = e.name === 'TimeoutError' ? '查询超时，请稍后重试。' : e.message }
  finally { busy.value = false; await scroll() }
}
async function scroll() { await nextTick(); if (conversation.value) conversation.value.scrollTop = conversation.value.scrollHeight }
function clear() { messages.value = [{role:'assistant',text:'开始一段新的天气对话吧。'}]; chatCity.value = null; mode.value = 'rules'; error.value = '' }

</script>

<template>
  <div class="shell">
    <header><a class="brand" href="/" aria-label="晴语首页"><span class="brand-icon">☀</span><span>晴语<small>WEATHER ASSISTANT</small></span></a><div class="header-note"><span class="status-dot"></span> 为每一天，做好晴雨准备</div><span class="tag">天气 · 生活 · 灵感</span></header>
    <main>
      <section class="intro"><div><div class="eyebrow">A LITTLE FORECAST, A BETTER DAY</div><h1>天气有变化，<span>出门有准备。</span></h1><p>看看天空的心情，安排属于你的一天。</p></div><div class="intro-art" aria-hidden="true"><span class="sun"></span><span class="cloud"></span></div></section>
      <div class="workspace">
        <aside>
          <section class="panel city-panel"><div class="section-head city-heading"><div class="city-heading-main"><h2>你所在的城市</h2><div class="current-location" role="status"><button class="location-trigger" :disabled="locating || weatherBusy" @click="locate" aria-label="重新定位" title="重新定位"><svg class="location-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg></button><span class="located-name" :title="locatedName">{{ locating ? '定位中…' : locatedName || '未获取位置' }}</span></div></div><span>LOCATION</span></div><p v-if="locationMessage" class="location-message" role="status">{{ locationMessage }}</p><form class="search" @submit.prevent="search()"><span aria-hidden="true">⌕</span><input v-model="query" aria-label="搜索城市" placeholder="搜索城市，如 北京 / Tokyo" maxlength="100"><button :disabled="searching" aria-label="搜索">{{ searching ? '…' : '→' }}</button></form><div class="popular-title">热门城市</div><div class="popular" role="group" aria-label="热门城市"><button v-for="name in popular" :key="name" :class="{ active: city?.name === name }" :aria-pressed="city?.name === name" :disabled="weatherBusy || searching" @click="choosePopular(name)">{{ name }}</button></div><p v-if="searchError" class="error" role="alert">{{ searchError }}</p><div v-if="results.length" class="results"><button v-for="r in results" :key="r.latitude+','+r.longitude" :disabled="weatherBusy" @click="choose(r)"><span>{{ r.name }}<small>{{ [r.region,r.country].filter(Boolean).join(' · ') }}</small></span><span>↗</span></button></div>
          <form class="region-picker" @submit.prevent="searchRegion">
            <div class="region-title">按省市区查询 <span>逐级选择所在地区</span></div>
            <div class="region-controls">
            <label>省份<select v-model="provinceCode" aria-label="省份" :disabled="weatherBusy || searching" @change="changeProvince"><option value="" disabled>请选择省份</option><option v-for="item in regions" :key="item.code" :value="item.code">{{ item.name }}</option></select></label>
            <label>城市<select v-model="cityCode" aria-label="城市" :disabled="!provinceCode || weatherBusy || searching" @change="changeCity"><option value="" disabled>请选择城市</option><option v-for="item in regionCities" :key="item.code" :value="item.code">{{ item.name }}</option></select></label>
            <label>区县<select v-model="districtCode" aria-label="区县" :disabled="!cityCode || weatherBusy || searching"><option value="" disabled>请选择区县</option><option v-for="item in districts" :key="item.code" :value="item.code">{{ item.name }}</option></select></label>
            <button class="region-search" :disabled="district?.latitude == null || weatherBusy || searching">{{ weatherBusy ? '查询中…' : '搜索天气' }} <span aria-hidden="true">→</span></button>
            </div>
            <p v-if="district && district.latitude == null" class="error" role="status">该区县暂缺坐标，请使用上方城市搜索查询。</p>
          </form></section>
          <section v-if="weather" class="weather-card"><div class="weather-top"><span><svg class="location-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg> {{ weather.city.name }}<small>{{ weather.city.region || weather.city.country }} · {{ weather.timezone }}</small></span><button :disabled="weatherBusy" @click="choose(city)" aria-label="刷新天气">↻</button></div><div class="condition"><span class="temperature">{{ Math.round(weather.current.temperature) }}<sup>°</sup></span><span class="weather-symbol" aria-hidden="true">{{ icon(weather.current.code) }}</span></div><p class="condition-label">{{ weather.current.description }}<span>体感 {{ weather.current.apparent }}°C</span></p><div class="weather-metrics"><div><small>相对湿度</small><strong>{{ weather.current.humidity }}<em>%</em></strong></div><div><small>风速</small><strong>{{ weather.current.wind }}<em>km/h</em></strong></div><div><small>今日降水概率</small><strong>{{ weather.days[0].rain ?? '—' }}<em>%</em></strong></div></div><div class="updated">数据时间 {{ weather.current.time.replace('T',' ') }} · 当地时间</div></section>
          <section v-else class="empty-weather panel"><span aria-hidden="true">☁</span><h3>{{ locating ? '正在定位当前位置…' : weatherBusy ? '正在看看天空…' : '下一站，什么天气？' }}</h3><p>搜索并选择城市，查看实时天气与七日预报。</p></section>
          <p v-if="weatherError" class="error weather-error" role="alert">{{ weatherError }}</p>
        </aside>
        <section v-show="chatOpen" id="weather-chat" class="panel chat-panel floating-chat" role="region" aria-labelledby="chat-title" @keydown.esc="closeChat"><div class="chat-head"><div class="assistant-avatar">☀</div><div><h2 id="chat-title">和晴语聊聊天气</h2><p>{{ chatCity ? '对话城市 · '+chatCity.name : '独立天气对话 · 请在问题中输入城市' }}</p></div><button class="clear" :disabled="busy" @click="clear">新对话 ↗</button><button class="chat-close" aria-label="收起问答助手" @click="closeChat">×</button></div><div ref="conversation" class="conversation" role="log" aria-live="polite"><div class="date-divider">TODAY · 今日天气灵感</div><div v-for="(message,index) in messages" :key="index" :class="['message',message.role]"><span v-if="message.role === 'assistant'" class="mini-avatar">☀</span><div><small>{{ message.role === 'assistant' ? '晴语' : '你' }}</small><p>{{ message.text }}</p></div></div><div v-if="busy" class="thinking"><span></span><span></span><span></span> 正在查询天气</div></div><div class="composer-area"><div v-if="error" class="error" role="alert">{{ error }} <button @click="send(messages.filter(m=>m.role==='user').at(-1)?.text || '今天天气')">重试</button></div><div class="suggestions"><button v-for="suggestion in suggestions" :key="suggestion" :disabled="busy" @click="send(suggestion)">{{ suggestion }} ↗</button></div><form class="composer" @submit.prevent="send()"><input ref="chatInput" v-model="input" aria-label="输入天气问题" placeholder="问问天气，比如“上海明天会下雨吗？”" maxlength="1000" :disabled="busy"><button :disabled="busy || !input.trim()" aria-label="发送消息">↑</button></form><div class="composer-footer"><span>Enter 发送</span></div></div></section>
      </div>
      <section v-if="weather" class="forecast panel"><div class="section-head"><h2>未来七天，心里有数</h2><span>{{ weather.city.name }} · 7-DAY FORECAST</span></div><div class="days"><article v-for="(day,i) in weather.days" :key="day.date"><div class="day-name">{{ dayLabel(day.date,i) }}</div><small>{{ day.date.slice(5).replace('-',' / ') }}</small><div class="day-icon" aria-hidden="true">{{ icon(day.code) }}</div><p>{{ day.description }}</p><strong>{{ Math.round(day.high) }}° <span>{{ Math.round(day.low) }}°</span></strong><div class="rain">降水 {{ day.rain ?? '—' }}%</div></article></div></section>
    </main><button ref="chatLauncher" class="chat-launcher" :aria-expanded="chatOpen" aria-controls="weather-chat" @click="toggleChat"><span aria-hidden="true">{{ chatOpen ? '⌄' : '☀' }}</span>{{ chatOpen ? '收起问答' : 'AI 天气助手' }}</button><footer><span>晴语 WEATHER ASSISTANT</span><span>把天气看明白，把日子过晴朗。</span></footer>
    <div class="source-note">气象数据来自 <a href="https://open-meteo.com/" target="_blank" rel="noopener noreferrer">Open-Meteo ↗</a><br>预报随时间变化，请以最新信息为准。</div>
  </div>
</template>
