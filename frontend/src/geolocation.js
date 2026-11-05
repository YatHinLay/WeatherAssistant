// 浏览器可能通过 GPS、Wi-Fi 或系统定位服务获取位置。
export function getCurrentLocation(env = globalThis) {
  if (!env.isSecureContext) return Promise.reject(new Error('定位需要 HTTPS 或 localhost，请改用安全地址访问。'))
  if (!env.navigator?.geolocation) return Promise.reject(new Error('当前浏览器不支持定位，请手动选择城市。'))
  return new Promise((resolve, reject) => {
    env.navigator.geolocation.getCurrentPosition(
      position => {
        const { latitude, longitude, accuracy } = position.coords
        if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || Math.abs(latitude) > 90 || Math.abs(longitude) > 180) {
          reject(new Error('未取得有效坐标，请重新定位或手动选择城市。'))
          return
        }
        resolve({name:'当前位置', latitude, longitude, country:'',
          region:Number.isFinite(accuracy) && accuracy >= 0 ? `浏览器定位 · 精度约 ${Math.ceil(accuracy)} 米` : '浏览器定位'})
      },
      error => reject(new Error({
        1:'定位权限被拒绝，请在浏览器中允许位置访问，或手动选择城市。',
        2:'暂时无法取得位置，请检查设备定位服务后重试，或手动选择城市。',
        3:'定位超时，请重新定位或手动选择城市。'
      }[error.code] || '定位失败，请重新定位或手动选择城市。')),
      {enableHighAccuracy:true, timeout:15000, maximumAge:60000}
    )
  })
}
