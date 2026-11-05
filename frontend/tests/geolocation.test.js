import test from 'node:test'
import assert from 'node:assert/strict'
import { getCurrentLocation } from '../src/geolocation.js'

test('定位成功返回实际坐标与精度，且只获取一次位置',async () => {
  let calls=0
  const place=await getCurrentLocation({isSecureContext:true,navigator:{geolocation:{getCurrentPosition(success,failure,options){
    calls++;assert.equal(options.enableHighAccuracy,true);assert.equal(options.timeout,15000)
    success({coords:{latitude:31.23,longitude:121.47,accuracy:21.2}})
  }}}})
  assert.equal(calls,1);assert.equal(place.latitude,31.23);assert.equal(place.longitude,121.47)
  assert.equal(place.name,'当前位置');assert.match(place.region,/22 米/)
})
test('拒绝权限、不可用及超时均提示手动选择',async () => {
  for (const code of [1,2,3]) await assert.rejects(getCurrentLocation({isSecureContext:true,navigator:{geolocation:{getCurrentPosition(success,failure){failure({code})}}}}),/手动选择城市/)
})
test('不安全环境和不支持定位时不请求位置',async () => {
  await assert.rejects(getCurrentLocation({isSecureContext:false}),/HTTPS/)
  await assert.rejects(getCurrentLocation({isSecureContext:true,navigator:{}}),/不支持定位/)
})
test('无效坐标不会用于天气查询',async () => {
  await assert.rejects(getCurrentLocation({isSecureContext:true,navigator:{geolocation:{getCurrentPosition(success){success({coords:{latitude:NaN,longitude:1}})}}}}),/有效坐标/)
})
