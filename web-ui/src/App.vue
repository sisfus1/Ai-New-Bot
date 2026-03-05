<template>
  <div class="min-h-screen bg-slate-50 text-slate-800 font-sans py-12 px-4 sm:px-6 lg:px-8 flex flex-col items-center">
    
    <div class="text-center mb-10">
      <h1 class="text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl flex items-center justify-center gap-3">
        <span class="text-5xl">🚀</span> 
        <span class="bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">Auto-Media-Agent</span> 
        控制台
      </h1>
      <p class="mt-4 text-lg text-slate-500 font-medium">
        企业级全自动新闻抓取、AI 大脑总结与多模态视频渲染流水线
      </p>
    </div>

    <div class="bg-white w-full max-w-3xl rounded-2xl shadow-xl border border-slate-100 p-8 sm:p-10 transition-all duration-300 hover:shadow-2xl">
      
      <div class="flex justify-center mb-8">
        <button 
          @click="generateVideo" 
          :disabled="isLoading"
          class="group relative inline-flex items-center justify-center px-8 py-4 text-lg font-bold text-white transition-all duration-200 bg-gradient-to-r from-blue-600 to-indigo-600 border border-transparent rounded-xl focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed hover:from-blue-700 hover:to-indigo-700 hover:scale-105"
        >
          <span class="mr-2 text-2xl group-hover:animate-bounce">🎬</span>
          {{ isLoading ? '流水线高速运转中...' : '一键生成今日多模态视频' }}
        </button>
      </div>

      <div class="bg-slate-50 rounded-xl p-6 border border-slate-200">
        <h3 class="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">系统状态监控</h3>
        
        <div class="flex items-center gap-3">
          <span class="relative flex h-4 w-4">
            <span v-if="isLoading" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-4 w-4" :class="statusColorClass"></span>
          </span>
          <span class="text-lg font-semibold text-slate-700">{{ statusText }}</span>
        </div>

        <div v-if="videoUrl" class="mt-8 animate-fade-in-up">
          <div class="rounded-xl overflow-hidden shadow-lg border border-slate-200 bg-black aspect-video flex items-center justify-center">
            <video 
              :src="videoUrl" 
              controls 
              autoplay 
              class="w-full h-full object-cover"
            ></video>
          </div>
          
          <div class="mt-4 flex items-center p-3 text-sm text-amber-700 bg-amber-50 rounded-lg border border-amber-200">
            <span class="font-bold mr-2">📂 资源路径:</span> 
            <a :href="videoUrl" target="_blank" class="hover:underline break-all">{{ videoUrl }}</a>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const statusText = ref('等待唤醒...')
const videoUrl = ref('')
const isLoading = ref(false)
let pollingInterval = null

// 根据不同状态返回 Tailwind 的颜色类名
const statusColorClass = computed(() => {
  if (isLoading.value) return 'bg-blue-500'
  if (statusText.value.includes('成功') || statusText.value.includes('完毕')) return 'bg-green-500'
  if (statusText.value.includes('失败') || statusText.value.includes('异常')) return 'bg-red-500'
  return 'bg-slate-300' // 默认灰色
})

const generateVideo = async () => {
  try {
    isLoading.value = true
    statusText.value = '🚀 正在初始化 RAG 大脑与多模态渲染流水线...'
    videoUrl.value = ''

    const response = await fetch('http://127.0.0.1:8000/api/tasks/generate_video', {
      method: 'POST'
    })
    
    if (!response.ok) throw new Error('网关请求失败')
    
    const data = await response.json()
    const taskId = data.task_id
    
    // 开始轮询状态
    pollingInterval = setInterval(async () => {
      const statusRes = await fetch(`http://127.0.0.1:8000/api/tasks/${taskId}`)
      const statusData = await statusRes.json()
      
      if (statusData.status.startsWith('SUCCESS')) {
        clearInterval(pollingInterval)
        statusText.value = '✅ 视频渲染完毕，准备播放！'
        videoUrl.value = statusData.status.split('SUCCESS: ')[1]
        isLoading.value = false
      } else if (statusData.status.startsWith('ERROR') || statusData.status.startsWith('FAILED')) {
        clearInterval(pollingInterval)
        statusText.value = `❌ 任务中断: ${statusData.status}`
        isLoading.value = false
      } else {
        // 动态增加一些有趣的极客状态提示
        statusText.value = '⚙️ Agent 正在疯狂调用底层算力，请耐心等待...'
      }
    }, 2000)

  } catch (error) {
    statusText.value = `⚠️ 系统严重异常: ${error.message}`
    isLoading.value = false
  }
}
</script>

<style>
/* 补充一个极简的自定义动画，Tailwind 默认没有内置这个，但这在大厂 UI 里很常用 */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in-up {
  animation: fadeInUp 0.6s ease-out forwards;
}
</style>