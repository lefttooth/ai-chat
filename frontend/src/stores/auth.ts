import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

interface User {
  id: number
  username: string
  email: string
  is_active: boolean
  created_at: string
}

interface LoginData {
  username: string
  password: string
}

interface RegisterData {
  username: string
  email: string
  password: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('token'))

  const isAuthenticated = computed(() => !!token.value)

  // 设置axios默认配置
  if (token.value) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
  }

  const login = async (loginData: LoginData) => {
    try {
      const formData = new FormData()
      formData.append('username', loginData.username)
      formData.append('password', loginData.password)
      
      const response = await axios.post('/api/token', formData)
      const { access_token } = response.data
      
      token.value = access_token
      localStorage.setItem('token', access_token)
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      
      // 获取用户信息
      await fetchUser()
      
      return { success: true }
    } catch (error: any) {
      return { 
        success: false, 
        error: error.response?.data?.detail || '登录失败' 
      }
    }
  }

  const register = async (registerData: RegisterData) => {
    try {
      const response = await axios.post('/api/register', registerData)
      return { success: true, user: response.data }
    } catch (error: any) {
      return { 
        success: false, 
        error: error.response?.data?.detail || '注册失败' 
      }
    }
  }

  const fetchUser = async () => {
    try {
      const response = await axios.get('/api/users/me')
      user.value = response.data
    } catch (error) {
      console.error('获取用户信息失败:', error)
    }
  }

  const logout = () => {
    user.value = null
    token.value = null
    localStorage.removeItem('token')
    delete axios.defaults.headers.common['Authorization']
  }

  return {
    user,
    token,
    isAuthenticated,
    login,
    register,
    fetchUser,
    logout
  }
}) 