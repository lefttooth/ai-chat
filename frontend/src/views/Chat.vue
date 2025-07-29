<template>
  <div class="chat-container">
    <!-- 侧边栏 -->
    <div class="sidebar">
      <div class="sidebar-header">
        <h3>AI对话</h3>
        <el-button 
          type="primary" 
          size="small" 
          @click="createNewChat"
          :icon="Plus"
        >
          新对话
        </el-button>
      </div>
      
      <!-- AI状态显示 -->
      <div class="ai-status">
        <div class="status-item">
          <el-icon :class="aiStatus.connected ? 'connected' : 'disconnected'">
            <CircleCheck v-if="aiStatus.connected" />
            <CircleClose v-else />
          </el-icon>
          <span>{{ aiStatus.connected ? 'AI已连接' : 'AI未连接' }}</span>
        </div>
        <div class="status-item" v-if="aiStatus.connected">
          <span class="model-name">{{ aiStatus.current_model }}</span>
        </div>
        <!-- 联网模式开关已移除 -->
      </div>
      
      <div class="conversation-list">
        <div 
          v-for="conversation in conversations" 
          :key="conversation.id"
          class="conversation-item"
          :class="{ active: currentConversationId === conversation.id }"
          @click="selectConversation(conversation.id)"
        >
          <span class="conversation-title">{{ conversation.title }}</span>
          <span class="conversation-time">{{ formatTime(conversation.created_at) }}</span>
          <el-button
            type="danger"
            size="small"
            icon="Delete"
            circle
            @click.stop="handleDeleteConversation(conversation.id)"
            style="float:right;margin-left:8px;"
            title="删除对话"
          />
        </div>
      </div>
      
      <div class="sidebar-footer">
        <el-dropdown @command="handleUserAction">
          <span class="user-info">
            <el-avatar :size="32" :icon="User" />
            <span>{{ authStore.user?.username }}</span>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
    
    <!-- 主聊天区域 -->
    <div class="chat-main">
      <div class="chat-header">
        <h2>{{ currentConversation?.title || '新对话' }}</h2>
      </div>
      
      <div class="chat-messages" ref="messagesContainer">
        <div 
          v-for="message in currentMessages" 
          :key="message.id"
          class="message"
          :class="message.role"
        >
          <div class="message-avatar">
            <el-avatar 
              :size="40" 
              :icon="message.role === 'user' ? User : Service"
            />
          </div>
          <div class="message-content">
            <div
              class="message-text"
              v-if="message.role === 'assistant'"
              v-html="renderMarkdown(message.content)"
            ></div>
            <div
              class="message-text"
              v-else
            >{{ message.content }}</div>
            <div class="message-time">{{ formatTime(message.created_at) }}</div>
          </div>
        </div>
        
        <div v-if="loading" class="message assistant">
          <div class="message-avatar">
            <el-avatar :size="40" :icon="Service" />
          </div>
          <div class="message-content">
            <div class="message-text">
              <el-icon class="is-loading"><Loading /></el-icon>
              正在思考...
            </div>
          </div>
        </div>
      </div>
      
      <div class="chat-input">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="2"
          placeholder="请输入内容，按Enter发送..."
          @keydown.enter.prevent="handleSendMessage"
          :disabled="!aiStatus.connected"
          class="custom-input"
        />
        <el-button 
          type="primary" 
          @click="handleSendMessage"
          :loading="loading"
          :disabled="!inputMessage.trim() || !aiStatus.connected"
          class="custom-send-btn"
        >
          <el-icon><ArrowDown style="transform:rotate(-90deg)" /></el-icon> 发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, Service, Plus, ArrowDown, Loading, CircleCheck, CircleClose, Delete } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import axios from 'axios'
import { marked } from 'marked'


const router = useRouter()
const authStore = useAuthStore()
const messagesContainer = ref<HTMLElement>()
const inputMessage = ref('')
const loading = ref(false)
const conversations = ref<any[]>([])
const currentConversationId = ref<number | null>(null)
const currentMessages = ref<any[]>([])
// AI状态
const aiStatus = ref({
  connected: false,
  current_model: '',
  available_models: []
})

const currentConversation = computed(() => {
  return conversations.value.find(c => c.id === currentConversationId.value)
})

onMounted(async () => {
  await fetchAIStatus()
  await fetchConversations()
  if (conversations.value.length > 0) {
    selectConversation(conversations.value[0].id)
  }
})

const fetchAIStatus = async () => {
  try {
    const response = await axios.get('/api/ai/status')
    aiStatus.value = response.data
  } catch (error) {
    console.error('获取AI状态失败:', error)
    aiStatus.value = {
      connected: false,
      current_model: '',
      available_models: []
    }
  }
}

const fetchConversations = async () => {
  try {
    const response = await axios.get('/api/conversations')
    conversations.value = response.data
  } catch (error) {
    console.error('获取对话列表失败:', error)
  }
}

const selectConversation = async (conversationId: number) => {
  currentConversationId.value = conversationId
  await fetchMessages(conversationId)
}

const fetchMessages = async (conversationId: number) => {
  try {
    const response = await axios.get(`/api/conversations/${conversationId}`)
    currentMessages.value = response.data.messages
    await nextTick()
    scrollToBottom()
  } catch (error) {
    console.error('获取消息失败:', error)
  }
}

const createNewChat = () => {
  currentConversationId.value = null
  currentMessages.value = []
  inputMessage.value = ''
}

const handleSendMessage = async () => {
  if (!inputMessage.value.trim() || loading.value || !aiStatus.value.connected) return

  const message = inputMessage.value.trim()
  inputMessage.value = ''
  loading.value = true

  // 立即在界面显示用户消息
  const tempId = Date.now()
  currentMessages.value.push({
    id: tempId,
    content: message,
    role: 'user',
    created_at: new Date().toISOString()
  })
  await nextTick()
  scrollToBottom()

  try {
    const response = await axios.post('/api/chat', {
      message,
      conversation_id: currentConversationId.value
    })

    // 如果是新对话，添加到对话列表
    if (!currentConversationId.value) {
      await fetchConversations()
      currentConversationId.value = response.data.conversation_id
    }

    // 用AI回复替换loading状态，并刷新消息（防止多端同步）
    await fetchMessages(response.data.conversation_id)

  } catch (error) {
    ElMessage.error('发送消息失败')
    // 失败时移除刚刚添加的用户消息
    currentMessages.value = currentMessages.value.filter(m => m.id !== tempId)
    console.error('发送消息失败:', error)
  } finally {
    loading.value = false
  }
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const formatTime = (timeString: string) => {
  const date = new Date(timeString)
  return date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function renderMarkdown(text: string) {
  return marked.parse(text || '')
}

const handleUserAction = async (command: string) => {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      })
      
      authStore.logout()
      router.push('/login')
      ElMessage.success('已退出登录')
    } catch {
      // 用户取消
    }
  }
}

const handleDeleteConversation = async (conversationId: number) => {
  try {
    await ElMessageBox.confirm('确定要删除该对话吗？', '提示', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await axios.delete(`/api/conversations/${conversationId}`)
    ElMessage.success('删除成功')
    await fetchConversations()
    // 如果删除的是当前对话，自动切换到第一个
    if (currentConversationId.value === conversationId) {
      if (conversations.value.length > 0) {
        selectConversation(conversations.value[0].id)
      } else {
        currentConversationId.value = null
        currentMessages.value = []
      }
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}
</script>

<style scoped>
.chat-container {
  display: flex;
  height: 100vh;
  background-color: #f5f5f5;
}

.sidebar {
  width: 300px;
  background-color: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h3 {
  margin: 0;
  color: #333;
}

.ai-status {
  padding: 15px 20px;
  border-bottom: 1px solid #e4e7ed;
  background-color: #f8f9fa;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
}

.status-item:last-child {
  margin-bottom: 0;
}

.status-item .el-icon {
  font-size: 16px;
}

.status-item .el-icon.connected {
  color: #67c23a;
}

.status-item .el-icon.disconnected {
  color: #f56c6c;
}

.model-name {
  font-size: 12px;
  color: #666;
  background-color: #e1f3d8;
  padding: 2px 8px;
  border-radius: 10px;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.conversation-item {
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 8px;
  transition: background-color 0.2s;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.conversation-item:hover {
  background-color: #f5f7fa;
}

.conversation-item.active {
  background-color: #ecf5ff;
  color: #409eff;
}

.conversation-title {
  display: block;
  font-weight: 500;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-time {
  font-size: 12px;
  color: #999;
}

.sidebar-footer {
  padding: 20px;
  border-top: 1px solid #e4e7ed;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
  transition: background-color 0.2s;
}

.user-info:hover {
  background-color: #f5f7fa;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #fff;
}

.chat-header {
  padding: 20px;
  border-bottom: 1px solid #e4e7ed;
}

.chat-header h2 {
  margin: 0;
  color: #333;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 80%;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message.assistant {
  align-self: flex-start;
}

.message-avatar {
  flex-shrink: 0;
}

.message-content {
  background-color: #f5f7fa;
  padding: 12px 16px;
  border-radius: 12px;
  position: relative;
}

.message.user .message-content {
  background-color: #409eff;
  color: #fff;
}

.message-text {
  line-height: 1.5;
  word-wrap: break-word;
}

.message-time {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.message.user .message-time {
  color: rgba(255, 255, 255, 0.8);
}

.chat-input {
  padding: 20px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  gap: 12px;
  align-items: flex-end;
  background: #f8fafd;
}

.chat-input .custom-input {
  flex: 1;
  border-radius: 8px;
  box-shadow: 0 2px 8px 0 rgba(64,158,255,0.06);
  background: #fff;
  font-size: 16px;
  min-height: 48px;
}

.chat-input .custom-send-btn {
  height: 44px;
  padding: 0 24px;
  font-size: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px 0 rgba(64,158,255,0.08);
  display: flex;
  align-items: center;
  gap: 6px;
}
</style> 