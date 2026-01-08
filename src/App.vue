<script setup>
  import { ref, onMounted, onUnmounted, watch } from 'vue'
  import mqtt from 'mqtt'
  
  // ========== 原有状态变量 ==========
  const selectedIMU = ref('') 
  const isConnected = ref(false)
  const receivedMessage = ref('暂无消息')
  let client = null
  const imuList = ref([]);
  
  // ========== 新增IMU曲线相关变量 ==========
  // Canvas实例管理
  let canvasInstance = null;
  // 动画帧标识
  let animationFrame = null;
  // 图表配置
  const CHART_CONFIG = {
    maxDataLength: 200, // 最大数据点数量
    accx: { color: '#ef4444', yMin: -60, yMax: 60 }, // X轴加速度配置
    accy: { color: '#3b82f6', yMin: -60, yMax: 60 }, // Y轴加速度配置
    accz: { color: '#22c55e', yMin: -60, yMax: 60 }  // Z轴加速度配置
  };
  // 数据源（三轴加速度）
  const dataSources = {
    accx: ref([]),
    accy: ref([]),
    accz: ref([])
  };
  // 当前显示的加速度值
  const accx = ref(0);
  const accy = ref(0);
  const accz = ref(0);
  
  // ========== 新增IMU曲线核心方法 ==========
  // 初始化Canvas
  const initPoseCanvas = () => {
    const canvas = document.getElementById('imu-chart');
    if (!canvas) return;
    
    // 设置Canvas尺寸（适配容器）
    const container = canvas.parentElement;
    canvas.width = container.clientWidth;
    canvas.height = canvas.clientHeight;
    
    const ctx = canvas.getContext('2d');
    canvasInstance = { canvas, ctx, width: canvas.width, height: canvas.height };
    
    // 开始绘制曲线
    startPoseDraw();
  };
  
  // 绘制IMU曲线（三轴加速度）
  const startPoseDraw = () => {
  if (!canvasInstance) return;

  const { ctx, width, height } = canvasInstance;
  const accxConfig = CHART_CONFIG.accx;
  const accyConfig = CHART_CONFIG.accy;
  const acczConfig = CHART_CONFIG.accz;

  const draw = () => {
    // ❗❗❗关键修改：每一帧彻底清屏（消除虚影）
    ctx.clearRect(0, 0, width, height);

    // 先画网格（避免覆盖曲线）
    drawGrid(ctx, width, height, 5, 5, accxConfig.yMin, accxConfig.yMax);

    const xStep = width / (CHART_CONFIG.maxDataLength - 1);

    // ===== X轴 =====
    if (dataSources.accx.value.length >= 2) {
      ctx.beginPath();
      ctx.strokeStyle = accxConfig.color;
      ctx.lineWidth = 1.5;
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';

      dataSources.accx.value.forEach((value, index) => {
        const x = index * xStep;
        const y =
          height -
          ((value - accxConfig.yMin) /
            (accxConfig.yMax - accxConfig.yMin)) *
            height;

        index === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });

      ctx.stroke();
    }

    // ===== Y轴 =====
    if (dataSources.accy.value.length >= 2) {
      ctx.beginPath();
      ctx.strokeStyle = accyConfig.color;
      ctx.lineWidth = 1.5;
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';

      dataSources.accy.value.forEach((value, index) => {
        const x = index * xStep;
        const y =
          height -
          ((value - accyConfig.yMin) /
            (accyConfig.yMax - accyConfig.yMin)) *
            height;

        index === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });

      ctx.stroke();
    }

    // ===== Z轴 =====
    if (dataSources.accz.value.length >= 2) {
      ctx.beginPath();
      ctx.strokeStyle = acczConfig.color;
      ctx.lineWidth = 1.5;
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';

      dataSources.accz.value.forEach((value, index) => {
        const x = index * xStep;
        const y =
          height -
          ((value - acczConfig.yMin) /
            (acczConfig.yMax - acczConfig.yMin)) *
            height;

        index === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });

      ctx.stroke();
    }

    animationFrame = requestAnimationFrame(draw);
  };

  if (animationFrame) cancelAnimationFrame(animationFrame);
  animationFrame = requestAnimationFrame(draw);
};

  
  // 绘制网格线辅助方法
  const drawGrid = (ctx, width, height, xDivisions, yDivisions, yMin, yMax) => {
    ctx.strokeStyle = 'rgba(200, 200, 200, 0.3)';
    ctx.lineWidth = 1;
    
    // 垂直网格线
    const xStep = width / xDivisions;
    for (let i = 1; i < xDivisions; i++) {
      ctx.beginPath();
      ctx.moveTo(i * xStep, 0);
      ctx.lineTo(i * xStep, height);
      ctx.stroke();
    }
    
    // 水平网格线
    const yStep = height / yDivisions;
    for (let i = 1; i < yDivisions; i++) {
      ctx.beginPath();
      ctx.moveTo(0, i * yStep);
      ctx.lineTo(width, i * yStep);
      ctx.stroke();
    }
    
    // 绘制Y轴范围文本
    // ctx.fillStyle = 'rgba(100, 100, 100, 0.7)';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(yMax.toString(), width - 5, 15);
    ctx.fillText(yMin.toString(), width - 5, height - 5);
  };
  
  // 重置IMU曲线
  const resetPoseChart = () => {
    if (!canvasInstance) return;
    
    const { ctx, width, height } = canvasInstance;
    ctx.clearRect(0, 0, width, height);
    
    // 清空数据源
    dataSources.accx.value = [];
    dataSources.accy.value = [];
    dataSources.accz.value = [];
    
    // 重置显示值
    accx.value = 0;
    accy.value = 0;
    accz.value = 0;
    
    // 重启绘制
    startPoseDraw();
  };
  
  // 处理窗口大小变化
  const handleWindowResize = () => {
    if (!canvasInstance) return;
    
    const canvas = canvasInstance.canvas;
    const container = canvas.parentElement;
    canvas.width = container.clientWidth;
    canvas.height = canvas.clientHeight;
    
    canvasInstance.width = canvas.width;
    canvasInstance.height = canvas.height;
  };
  
  // ========== 新增IMU数据更新方法 ==========
  const updatePoseData = (mqttData) => {
    // 只处理选中的IMU设备数据
    if (mqttData.n !== selectedIMU.value) return;
  
    // 更新当前显示值
    accx.value = parseFloat(mqttData.accx) || 0;
    accy.value = parseFloat(mqttData.accy) || 0;
    accz.value = parseFloat(mqttData.accz) || 0;
  
    // 更新数据源（保持最大长度）
    dataSources.accx.value.push(accx.value);
    dataSources.accy.value.push(accy.value);
    dataSources.accz.value.push(accz.value);
    
    if (dataSources.accx.value.length > CHART_CONFIG.maxDataLength) {
      dataSources.accx.value.shift();
      dataSources.accy.value.shift();
      dataSources.accz.value.shift();
    }
  };
  
  // ========== 监听选中的IMU变化 ==========
  watch(selectedIMU, (newVal, oldVal) => {
    if (newVal !== oldVal && newVal) {
      resetPoseChart();
    }
  });
  
  // ========== 原有MQTT连接逻辑 ==========
  onMounted(() => {
    // 1. 连接公共MQTT测试服务器
    const brokerUrl = 'ws://123.207.9.26:8083/mqtt';
    client = mqtt.connect(brokerUrl, {
      clientId: `vue_${Date.now()}_${Math.floor(Math.random() * 10000)}`,
      clean: true,
      connectTimeout: 4000,
      username: 'admin',
      password: '@Szu123456',
      reconnectPeriod: 1000,
    });
  
    // 2. 监听连接成功事件
    client.on('connect', () => {
      console.log('MQTT 连接成功！');
      isConnected.value = true;
      const topic = 'IMU-MQTT';
      client.subscribe(topic, (err) => {
        if (!err) {
          console.log(`成功订阅主题：${topic}`);
        } else {
          console.error('订阅主题失败：', err);
        }
      });
    });
  
    // 3. 监听收到消息事件
    client.on('message', (topic, payload) => {
      receivedMessage.value = payload.toString();
      const rawMsg = payload.toString().trim();
      
      try {
        const jsonRegex = /\{[\s\S]*?\}/g;
        const jsonArray = rawMsg.match(jsonRegex) || [];
        
        const parsedMessages = jsonArray
          .filter(Boolean)
          .map(item => {
            try {
              return JSON.parse(item);
            } catch (parseErr) {
              console.warn(`解析单条JSON失败:`, item, parseErr);
              return null;
            }
          })
          .filter(Boolean);
  
        parsedMessages.forEach(mqttData => {
          // 解析IMU名称并添加到列表
          const imuName = mqttData?.n;
          if (imuName && !imuList.value.includes(imuName)) {
            imuList.value.push(imuName);
            // 默认选中第一个IMU设备
            if (imuList.value.length === 1) {
              selectedIMU.value = imuName;
            }
          }
          
          // 更新IMU曲线数据
          updatePoseData(mqttData);
        });
  
      } catch (error) {
        console.error(`解析MQTT消息失败:`, error);
      }
    });
  
    // 4. 监听连接错误事件
    client.on('error', (err) => {
      console.error('MQTT 连接错误：', err);
      isConnected.value = false;
    });
  
    // 5. 监听断开连接事件
    client.on('close', () => {
      console.log('MQTT 连接已断开');
      isConnected.value = false;
    });
  
    // 初始化IMU曲线Canvas
    setTimeout(() => {
      initPoseCanvas();
    }, 100);
    
    // 监听窗口大小变化
    window.addEventListener('resize', handleWindowResize);
  });
  
  // ========== 组件卸载清理 ==========
  onUnmounted(() => {
    // 断开MQTT连接
    if (client && client.connected) {
      client.end();
      console.log('MQTT 连接已主动断开');
    }
    
    // 停止动画帧
    if (animationFrame) cancelAnimationFrame(animationFrame);
    
    // 移除事件监听
    window.removeEventListener('resize', handleWindowResize);
    
    // 清空数据源
    dataSources.accx.value = [];
    dataSources.accy.value = [];
    dataSources.accz.value = [];
  });
  </script>
  
  <template>
    <div class="p-6 max-w-7xl mx-auto">
      <!-- IMU选择下拉框 -->
      <div class="w-32 mb-6">
        <label class="block text-sm font-medium text-gray-700 mb-1">
          选择IMU设备
        </label>
        <select
          v-model="selectedIMU"
          class="w-full px-2 py-1 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
          :disabled="!imuList.length"
        >
          <option value="" disabled v-if="!imuList.length">暂无IMU设备</option>
          <option 
            v-for="item in imuList"  
            :key="item"             
            :value="item"          
          >
            {{ item }}
          </option>
        </select>
      </div>
  
      <!-- IMU曲线绘制区域 -->
      <div class="bg-white rounded-2xl shadow p-6 mb-6">
        <h3 class="text-lg font-semibold mb-4 flex items-center">
          <span class="mr-2 text-green-500">📊</span>
          IMU三轴加速度曲线 ({{ selectedIMU || '未选择设备' }})
        </h3>
        <!-- Canvas容器 -->
        <div class="w-full h-64 mb-4">
          <canvas id="imu-chart" class="w-full h-full rounded"></canvas>
        </div>
        <!-- 实时数值显示 -->
        <div class="flex justify-between pt-4 border-t border-gray-100">
          <div class="text-center">
            <div class="text-2xl font-bold text-red-500">
              {{ accx.toFixed(2) }}
            </div>
            <div class="text-xs text-gray-500">X轴加速度(g)</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-blue-500">
              {{ accy.toFixed(2) }}
            </div>
            <div class="text-xs text-gray-500">Y轴加速度(g)</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-green-500">
              {{ accz.toFixed(2) }}
            </div>
            <div class="text-xs text-gray-500">Z轴加速度(g)</div>
          </div>
        </div>
      </div>
  
      <!-- MQTT消息展示文本框 -->
      <div class="mb-6">
        <label class="block text-sm font-medium text-gray-700 mb-1">
          当前接收的MQTT消息
          <span class="ml-2 text-xs text-gray-500">
            {{ isConnected ? '（已连接）' : '（未连接）' }}
          </span>
        </label>
        <textarea
          v-model="receivedMessage"
          class="w-full h-40 px-3 py-2 border border-gray-300 rounded-lg 
                focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent 
                transition-all font-mono text-sm bg-gray-50 resize-y"
          readonly
          placeholder="等待接收MQTT消息..."
          wrap="soft"
          spellcheck="false"
        ></textarea>
        <!-- 消息长度提示 -->
        <p class="mt-1 text-xs text-gray-500">
          消息长度: {{ receivedMessage.length }} 字符 | IMU设备数: {{ imuList.length }}
        </p>
      </div>
    </div>
  </template>
  
  <style scoped>
  /* 下拉框禁用样式 */
  select:disabled {
    background-color: #f5f5f5;
    cursor: not-allowed;
  }
  
  /* Canvas容器样式 */
  canvas {
    display: block;
  }
  </style>
