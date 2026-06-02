<script setup>
import { computed, onMounted, ref } from 'vue'
import { fetchProducts, sendChatMessage } from './api/client'

const sessionId = ref(null)
const input = ref('我想买一台适合剪视频的笔记本，预算 8000')
const loading = ref(false)
const error = ref('')
const messages = ref([
  {
    role: 'assistant',
    content: '说一下你想买什么、预算和使用场景，我会筛选并对比候选商品。'
  }
])
const products = ref([])
const comparison = ref(null)
const catalog = ref([])
const steps = ref([])

const history = computed(() =>
  messages.value.map((message) => ({
    role: message.role,
    content: message.content
  }))
)

const topProduct = computed(() => products.value[0] || null)

onMounted(async () => {
  try {
    catalog.value = await fetchProducts()
  } catch (err) {
    error.value = '商品库加载失败，请确认后端服务已启动。'
  }
})

async function submitMessage() {
  const message = input.value.trim()
  if (!message || loading.value) return

  error.value = ''
  messages.value.push({ role: 'user', content: message })
  input.value = ''
  loading.value = true

  try {
    const response = await sendChatMessage({
      message,
      session_id: sessionId.value,
      history: history.value
    })

    sessionId.value = response.session_id
    messages.value.push({ role: 'assistant', content: response.reply })
    products.value = response.products || []
    comparison.value = response.comparison
    steps.value = response.steps || []
  } catch (err) {
    error.value = '请求失败，请确认 FastAPI 服务运行在 8000 端口。'
  } finally {
    loading.value = false
  }
}

function usePrompt(prompt) {
  input.value = prompt
}

function formatPrice(price) {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    maximumFractionDigits: 0
  }).format(price)
}
</script>

<template>
  <main class="app-shell">
    <section class="workspace">
      <div class="chat-panel">
        <header class="topbar">
          <div>
            <p class="eyebrow">Shopping Agent</p>
            <h1>智能购物助手</h1>
          </div>
          <span class="status-dot">LLM + Mock</span>
        </header>

        <div class="quick-prompts">
          <button type="button" @click="usePrompt('我想买一台适合剪视频的笔记本，预算 8000')">
            剪视频笔记本
          </button>
          <button type="button" @click="usePrompt('2000 元以内通勤降噪耳机')">
            降噪耳机
          </button>
          <button type="button" @click="usePrompt('适合编程的无线机械键盘，预算 800')">
            编程键盘
          </button>
        </div>

        <div class="messages" aria-live="polite">
          <article
            v-for="(message, index) in messages"
            :key="`${message.role}-${index}`"
            class="message"
            :class="message.role"
          >
            <p>{{ message.content }}</p>
          </article>
        </div>

        <form class="composer" @submit.prevent="submitMessage">
          <textarea
            v-model="input"
            rows="3"
            placeholder="输入商品需求、预算和使用场景"
            :disabled="loading"
          />
          <button type="submit" :disabled="loading || !input.trim()">
            {{ loading ? '筛选中' : '发送' }}
          </button>
        </form>

        <p v-if="error" class="error">{{ error }}</p>
      </div>

      <aside class="results-panel">
        <section v-if="steps.length" class="result-block">
          <div class="section-heading">
            <h2>执行过程</h2>
            <span>{{ steps.length }} 步</span>
          </div>

          <ol class="agent-steps">
            <li v-for="step in steps" :key="step">{{ step }}</li>
          </ol>
        </section>

        <section class="result-block">
          <div class="section-heading">
            <h2>候选商品</h2>
            <span>{{ products.length || catalog.length }} 件</span>
          </div>

          <div v-if="topProduct" class="top-pick">
            <span>优先推荐</span>
            <strong>{{ topProduct.name }}</strong>
            <small>{{ formatPrice(topProduct.price) }}</small>
          </div>

          <div class="product-list">
            <article
              v-for="product in products.length ? products : catalog.slice(0, 4)"
              :key="product.id"
              class="product-card"
            >
              <img :src="product.image" :alt="product.name" />
              <div>
                <div class="product-title">
                  <h3>{{ product.name }}</h3>
                  <strong>{{ formatPrice(product.price) }}</strong>
                </div>
                <p>{{ product.brand }} · 评分 {{ product.rating }} · 销量 {{ product.sales }}</p>
                <div class="tags">
                  <span v-for="tag in product.tags.slice(0, 4)" :key="tag">{{ tag }}</span>
                </div>
                <ul v-if="product.match_reasons?.length" class="reasons">
                  <li v-for="reason in product.match_reasons.slice(0, 3)" :key="reason">
                    {{ reason }}
                  </li>
                </ul>
              </div>
            </article>
          </div>
        </section>

        <section v-if="comparison" class="result-block comparison-block">
          <div class="section-heading">
            <h2>对比结论</h2>
          </div>

          <p class="decision-note">{{ comparison.decision_note }}</p>

          <div class="compare-table">
            <article v-for="item in comparison.items" :key="item.product_id" class="compare-item">
              <h3>{{ item.name }}</h3>
              <p>{{ item.summary }}</p>
              <strong>优势</strong>
              <span>{{ item.strengths.join('，') }}</span>
              <strong>短板</strong>
              <span>{{ item.weaknesses.join('，') }}</span>
            </article>
          </div>
        </section>
      </aside>
    </section>
  </main>
</template>
