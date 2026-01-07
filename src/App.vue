<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import mqtt from 'mqtt'

// 状态变量：连接状态、接收的消息
const selectedIMU = ref('imu1') 
const isConnected = ref(false)
const receivedMessage = ref('暂无消息')
// 保存mqtt客户端实例，方便后续断开连接
let client = null
let imuList = ref([]);
onMounted(() => {
  // 1. 连接公共MQTT测试服务器（EMQ X提供，稳定可用）
  const brokerUrl = 'ws://123.207.9.26:8083/mqtt' // 用wss协议，避免浏览器跨域问题
  // 也可以用mqtt://broker.emqx.io:1883（非浏览器环境用）
  client = mqtt.connect(brokerUrl, {
    clientId: `vue`, // 随机客户端ID
    clean: true,
    connectTimeout: 4000,
    username: 'admin', // 测试账号（可选）
    password: '@Szu123456',
    reconnectPeriod: 1000, // 重连间隔
  })

  // 2. 监听连接成功事件
  client.on('connect', () => {
    console.log('MQTT 连接成功！')
    isConnected.value = true
    // 3. 订阅测试主题（可以自己替换成你需要的主题）
    const topic = 'IMU-MQTT'
    client.subscribe(topic, (err) => {
      if (!err) {
        console.log(`成功订阅主题：${topic}`)
        // 可选：订阅成功后发布一条测试消息给自己
        client.publish(topic, '这是Vue发送的测试MQTT消息')
      } else {
        console.error('订阅主题失败：', err)
      }
    })
  })

  // 4. 监听收到消息事件
  client.on('message', (topic, payload) => {
    const rawMsg = payload.toString().trim();
          try {
            let jsonArray = [];
            const jsonRegex = /\{[\s\S]*?\}/g;
            jsonArray = rawMsg.match(jsonRegex) || [];
            
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

            // mqttData是解析到的单条数据
            parsedMessages.forEach(mqttData => {
                // 1、解析IMU名称（确保mqttData.n存在且为有效字符串）
                const imuName = mqttData?.n; // 使用可选链避免空值报错
                
                // 2、监测IMU名称是否在列表中，不存在则添加
                if (!imuList.value.includes(imuName)) {
                  imuList.value.push(imuName);
                  // 可选：添加日志便于调试
                  console.log(`新增IMU设备: ${imuName}`);
                }
            });

          } catch (error) {
            console.error(`解析MQTT消息失败:`, error);
          }
    
  })

  // 5. 监听连接错误事件
  client.on('error', (err) => {
    console.error('MQTT 连接错误：', err)
    isConnected.value = false
  })

  // 6. 监听断开连接事件
  client.on('close', () => {
    console.log('MQTT 连接已断开')
    isConnected.value = false
  })
})

// 组件卸载时断开MQTT连接，避免内存泄漏
onUnmounted(() => {
  if (client && client.connected) {
    client.end()
    console.log('MQTT 连接已主动断开')
  }
})
</script>


<template>
  <!-- IMU选择下拉框 -->
  <div class="w-32 ml-2">
    <select
      v-model="selectedIMU"
      class="w-full px-2 py-0.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
    >
      <!-- 关键修改：用v-for遍历imu数组，生成每个option -->
      <option 
        v-for="item in imuList"  
        :key="item"             
        :value="item"          
      >
      {{ item }}  <!-- 显示当前item为下拉文本 -->
      </option>
    </select>
  </div>
</template>


<style scoped></style>
