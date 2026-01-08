<script setup>
  import { ref, onMounted, onUnmounted, watch } from 'vue'
  import mqtt from 'mqtt'
  
  // ====== 原有状态变量 ======
  const selectedIMU = ref('')
  const isConnected = ref(false)
  const receivedMessage = ref('暂无消息')
  let client = null
  
  // 所有IMU设备列表
  const imuList = ref([])
  // 每个IMU设备对应的频率
  const imuRates = ref({})  // { [imuName]: rate }
  
  // ====== 新增IMU曲线相关变量 ======
  let canvasInstance = null
  let animationFrame = null
  const CHART_CONFIG = {
    maxDataLength: 200,
    accx: { color: '#ef4444', yMin: -60, yMax: 60, lineWidth: 2.5 },
    accy: { color: '#3b82f6', yMin: -60, yMax: 60, lineWidth: 2.5 },
    accz: { color: '#22c55e', yMin: -60, yMax: 60, lineWidth: 2.5 }
  }
  const dataSources = {
    accx: ref([]),
    accy: ref([]),
    accz: ref([])
  }
  const accx = ref(0)
  const accy = ref(0)
  const accz = ref(0)
  
  // 当前显示的平滑值
  const accxDisplay = ref(0)
  const accyDisplay = ref(0)
  const acczDisplay = ref(0)
  let valueAnimationTimer = null
  
  // ====== 频率统计 ======
  let imuMsgCountMap = {} // { [imuName]: count }
  let rateTimer = null
  
  // ====== 初始化 Canvas ======
  const initPoseCanvas = () => {
    const canvas = document.getElementById('imu-chart')
    if (!canvas) return
  
    const container = canvas.parentElement
    const dpr = window.devicePixelRatio || 1
    const cssWidth = container.clientWidth
    const cssHeight = container.clientHeight
  
    canvas.width = cssWidth * dpr
    canvas.height = cssHeight * dpr
    canvas.style.width = cssWidth + 'px'
    canvas.style.height = cssHeight + 'px'
  
    const ctx = canvas.getContext('2d')
    ctx.scale(dpr, dpr)
  
    canvasInstance = { canvas, ctx, width: cssWidth, height: cssHeight }
    startPoseDraw()
  }
  
  // ====== 绘制IMU曲线 ======
  const startPoseDraw = () => {
    if (!canvasInstance) return
    const { ctx, width, height } = canvasInstance
    const accxConfig = CHART_CONFIG.accx
    const accyConfig = CHART_CONFIG.accy
    const acczConfig = CHART_CONFIG.accz
  
    const draw = () => {
      ctx.clearRect(0, 0, width, height)
      drawGrid(ctx, width, height, 5, 5, accxConfig.yMin, accxConfig.yMax)
      const xStep = width / (CHART_CONFIG.maxDataLength - 1)
  
      const drawLine = (data, config) => {
        if (data.length < 2) return
        ctx.beginPath()
        ctx.strokeStyle = config.color
        ctx.lineWidth = config.lineWidth
        ctx.lineJoin = 'round'
        ctx.lineCap = 'round'
        data.forEach((value, index) => {
          const x = index * xStep
          const y = height - ((value - config.yMin) / (config.yMax - config.yMin)) * height
          index === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
        })
        ctx.stroke()
      }
  
      drawLine(dataSources.accx.value, accxConfig)
      drawLine(dataSources.accy.value, accyConfig)
      drawLine(dataSources.accz.value, acczConfig)
  
      animationFrame = requestAnimationFrame(draw)
    }
  
    if (animationFrame) cancelAnimationFrame(animationFrame)
    animationFrame = requestAnimationFrame(draw)
  }
  
  // ====== 绘制网格 ======
  const drawGrid = (ctx, width, height, xDivisions, yDivisions, yMin, yMax) => {
    ctx.strokeStyle = 'rgba(200,200,200,0.3)'
    ctx.lineWidth = 1
    const xStep = width / xDivisions
    const yStep = height / yDivisions
  
    for (let i = 1; i < xDivisions; i++) {
      ctx.beginPath()
      ctx.moveTo(i * xStep, 0)
      ctx.lineTo(i * xStep, height)
      ctx.stroke()
    }
    for (let i = 1; i < yDivisions; i++) {
      ctx.beginPath()
      ctx.moveTo(0, i * yStep)
      ctx.lineTo(width, i * yStep)
      ctx.stroke()
    }
    ctx.font = '10px sans-serif'
    ctx.textAlign = 'right'
    ctx.fillText(yMax.toString(), width - 5, 15)
    ctx.fillText(yMin.toString(), width - 5, height - 5)
  }
  
  // ====== 重置曲线 ======
  const resetPoseChart = () => {
    if (!canvasInstance) return
    const { ctx, width, height } = canvasInstance
    ctx.clearRect(0, 0, width, height)
    dataSources.accx.value = []
    dataSources.accy.value = []
    dataSources.accz.value = []
    accx.value = 0
    accy.value = 0
    accz.value = 0
    startPoseDraw()
  }
  
  // ====== 初始化频率统计 ======
  const initRateTimer = () => {
    if (rateTimer) clearInterval(rateTimer)
    imuMsgCountMap = {}
    imuRates.value = {}
    rateTimer = setInterval(() => {
      for (const imu of imuList.value) {
        imuRates.value[imu] = imuMsgCountMap[imu] || 0
        imuMsgCountMap[imu] = 0
      }
    }, 1000)
  }
  
  // ====== 平滑动画 ======
  const animateValues = () => {
    const delta = 0.1
    accxDisplay.value += (accx.value - accxDisplay.value) * delta
    accyDisplay.value += (accy.value - accyDisplay.value) * delta
    acczDisplay.value += (accz.value - acczDisplay.value) * delta
    if (valueAnimationTimer) cancelAnimationFrame(valueAnimationTimer)
    valueAnimationTimer = requestAnimationFrame(animateValues)
  }
  
  // ====== 更新IMU数据 ======
  const updatePoseData = (mqttData) => {
    if (mqttData.n !== selectedIMU.value) return
    const imuName = mqttData.n
  

    accx.value = parseFloat(mqttData.accx) || 0
    accy.value = parseFloat(mqttData.accy) || 0
    accz.value = parseFloat(mqttData.accz) || 0
  
    dataSources.accx.value.push(accx.value)
    dataSources.accy.value.push(accy.value)
    dataSources.accz.value.push(accz.value)
    if (dataSources.accx.value.length > CHART_CONFIG.maxDataLength) {
      dataSources.accx.value.shift()
      dataSources.accy.value.shift()
      dataSources.accz.value.shift()
    }
  }
  
  // ====== 监听选中IMU变化 ======
  watch(selectedIMU, (newVal, oldVal) => {
    if (newVal !== oldVal && newVal) {
      resetPoseChart()
    }
  })

  
  // ====== MQTT连接逻辑 ======
  onMounted(() => {
    initRateTimer()
    const brokerUrl = 'ws://123.207.9.26:8083/mqtt'
    client = mqtt.connect(brokerUrl, {
      clientId: `vue_${Date.now()}_${Math.floor(Math.random() * 10000)}`,
      clean: true,
      connectTimeout: 4000,
      username: 'admin',
      password: '@Szu123456',
      reconnectPeriod: 1000
    })
  
    client.on('connect', () => {
      console.log('MQTT 连接成功！')
      isConnected.value = true
      client.subscribe('IMU-MQTT')
    })
  
    client.on('message', (topic, payload) => {
      const rawMsg = payload.toString().trim()
      
      imuList.value.forEach(imuName => {
      // 跳过空值，且确保同一消息中同一设备只计数一次
      if (imuName  && rawMsg.includes(imuName)) {
        imuMsgCountMap[imuName] = (imuMsgCountMap[imuName] || 0) + 1
      }
    })

      const jsonRegex = /\{[\s\S]*?\}/g
      const jsonArray = rawMsg.match(jsonRegex) || []
  
      const parsedMessages = jsonArray
        .map(item => { try { return JSON.parse(item) } catch { return null } })
        .filter(Boolean)
  
      parsedMessages.forEach(mqttData => {
        const imuName = mqttData.n
        if (imuName && !imuList.value.includes(imuName)) {
          imuList.value.push(imuName)
              // 自动选中第一个设备
          if (!selectedIMU.value) {
            selectedIMU.value = imuName
          }
        }
        updatePoseData(mqttData)
        if (mqttData.n == selectedIMU.value){
          receivedMessage.value = rawMsg
        }
        
      })
    })
  
    client.on('error', () => isConnected.value = false)
    client.on('close', () => isConnected.value = false)
  
    setTimeout(initPoseCanvas, 100)
    window.addEventListener('resize', () => {
      if (!canvasInstance) return
      const canvas = canvasInstance.canvas
      const container = canvas.parentElement
      canvas.width = container.clientWidth
      canvas.height = container.clientHeight
      canvasInstance.width = canvas.width
      canvasInstance.height = canvas.height
    })
  
    animateValues()
  })
  
  onUnmounted(() => {
    if (client && client.connected) client.end()
    if (animationFrame) cancelAnimationFrame(animationFrame)
    if (rateTimer) clearInterval(rateTimer)
    window.removeEventListener('resize', handleWindowResize)
  })
  </script>
  
  <template>
  <div class="w-full h-screen flex flex-col p-4 bg-gradient-to-br from-gray-50 to-gray-100">
    <!-- 上部文本区 30% -->
    <div class="flex-[0.3] overflow-auto mb-4 space-y-4">
      <!-- IMU选择 -->
      <div class="bg-white rounded-xl shadow-sm p-4 border border-gray-200">
        <label class="block text-sm font-semibold text-gray-700 mb-2">选择IMU设备</label>
        <select v-model="selectedIMU" class="w-full px-4 py-3 bg-gray-50 border border-gray-300 rounded-lg">
          <option v-if="!imuList.length" value="" disabled>暂无IMU设备</option>
          <option v-for="item in imuList" :key="item" :value="item">{{ item }}</option>
        </select>
      </div>
  
      <!-- MQTT消息 -->
      <div class="bg-white rounded-2xl shadow-lg p-4 border border-gray-200 h-[50%] overflow-auto">
        <h3 class="text-lg font-bold mb-2">MQTT原始消息</h3>
        <pre class="whitespace-pre-wrap break-all text-gray-700">{{ receivedMessage }}</pre>
      </div>
  
      <!-- 连接状态 -->
      <div class="bg-white rounded-2xl shadow-lg p-4 border border-gray-200">
        <h3 class="text-lg font-bold mb-2">连接状态</h3>
        <div v-if="!imuList.length" class="text-gray-500">暂无IMU设备</div>
        <div v-else class="space-y-2">
          <div v-for="imu in imuList" :key="imu" class="flex justify-between items-center p-2 bg-gray-50 rounded-lg border border-gray-200">
            <span class="font-medium">{{ imu }}</span>
            <span :class="imuRates[imu] ? 'text-green-600' : 'text-red-500'">
             : {{ imuRates[imu] || 0 }} Hz
            </span>
          </div>
        </div>
      </div>
    </div>
  
    <!-- 下部图像区 70% -->
    <div class="flex-[0.7] bg-white rounded-2xl shadow-lg p-4 border border-gray-200 flex flex-col">
      <h3 class="text-xl font-bold mb-2">IMU三轴加速度实时曲线</h3>
      <div class="flex-1 bg-gradient-to-b from-gray-50 to-white rounded-xl p-2 mb-4">
        <canvas id="imu-chart" class="w-full h-full rounded-lg"></canvas>
      </div>
  
      <div class="grid grid-cols-4 gap-4">
        <div class="bg-red-50 p-2 rounded-xl text-center">
          <div class="text-sm font-medium text-gray-600">X轴: {{ accx.toFixed(2) }}  Y轴: {{ accy.toFixed(2) }}   Z轴: {{ accz.toFixed(2) }}</div>
          <div class="text-2xl font-bold text-red-600"></div>
        </div>
      </div>
    </div>
  </div>
  </template>
  