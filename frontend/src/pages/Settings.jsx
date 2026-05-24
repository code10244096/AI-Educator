import React, { useState } from 'react'
import {
  User,
  School,
  Bell,
  Palette,
  Shield,
  Database,
  Save,
  ChevronRight,
  Moon,
  Sun,
  Monitor,
  Upload,
  Trash2,
  Download,
  Key,
  Mail,
  Phone,
  Camera,
  Edit,
  X
} from 'lucide-react'
import { useClass } from '../context/ClassContext'
import { useToast } from '../components/Toast'
import ConfirmDialog from '../components/ConfirmDialog'

const Settings = () => {
  const { classes, addClass, updateClass, deleteClass } = useClass()
  const { addToast } = useToast()
  const [activeSection, setActiveSection] = useState('profile')
  const [theme, setTheme] = useState('light')
  const [notifications, setNotifications] = useState({
    email: true,
    browser: true,
    homework: true,
    alert: true,
  })
  const [showAddClass, setShowAddClass] = useState(false)
  const [editingClass, setEditingClass] = useState(null)
  const [editForm, setEditForm] = useState({ name: '', subject: '', students: 0, grade: '' })
  const [newClass, setNewClass] = useState({
    name: '',
    subject: '数学',
    students: 45,
    grade: '高三',
  })
  const [profile, setProfile] = useState({
    name: '李老师',
    email: 'li.teacher@school.edu.cn',
    phone: '138****1234',
  })
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const [passwordForm, setPasswordForm] = useState({ old: '', new: '', confirm: '' })
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteTargetId, setDeleteTargetId] = useState(null)
  
  const handleAddClass = () => {
    if (!newClass.name) {
      addToast('请输入班级名称', 'error')
      return
    }
    addClass(newClass)
    setNewClass({ name: '', subject: '数学', students: 45, grade: '高三' })
    setShowAddClass(false)
    addToast('班级创建成功', 'success')
  }
  
  const handleDeleteClass = (id) => {
    setDeleteTargetId(id)
    setShowDeleteConfirm(true)
  }
  
  const confirmDelete = () => {
    deleteClass(deleteTargetId)
    setShowDeleteConfirm(false)
    setDeleteTargetId(null)
    addToast('班级已删除', 'success')
  }
  
  const handleEditClass = (cls) => {
    setEditingClass(cls.id)
    setEditForm({ name: cls.name, subject: cls.subject, students: cls.students, grade: cls.grade })
  }
  
  const handleSaveEdit = () => {
    updateClass(editingClass, editForm)
    setEditingClass(null)
    addToast('班级信息已更新', 'success')
  }
  
  const handleSaveProfile = () => {
    addToast('个人资料已保存', 'success')
  }
  
  const handleChangePassword = () => {
    if (!passwordForm.old || !passwordForm.new || !passwordForm.confirm) {
      addToast('请填写完整密码信息', 'error')
      return
    }
    if (passwordForm.new !== passwordForm.confirm) {
      addToast('两次输入的新密码不一致', 'error')
      return
    }
    if (passwordForm.new.length < 6) {
      addToast('新密码长度不能少于6位', 'error')
      return
    }
    addToast('密码修改成功', 'success')
    setPasswordForm({ old: '', new: '', confirm: '' })
    setShowPasswordModal(false)
  }
  
  const handleExportData = () => {
    const data = JSON.stringify({ classes, profile, notifications }, null, 2)
    const blob = new Blob([data], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `教学助手数据_${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    addToast('数据导出成功', 'success')
  }
  
  const handleClearCache = () => {
    localStorage.clear()
    sessionStorage.clear()
    addToast('缓存已清除', 'success')
  }
  
  const sections = [
    { id: 'profile', label: '个人资料', icon: User },
    { id: 'class', label: '班级管理', icon: School },
    { id: 'notification', label: '通知设置', icon: Bell },
    { id: 'appearance', label: '外观设置', icon: Palette },
    { id: 'security', label: '安全设置', icon: Shield },
    { id: 'data', label: '数据管理', icon: Database },
  ]
  
  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900">设置</h2>
        <p className="text-sm text-gray-500 mt-1">管理个人资料与系统设置</p>
      </div>
      
      <div className="flex gap-6">
        <div className="w-56 flex-shrink-0">
          <nav className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            {sections.map((section) => {
              const Icon = section.icon
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full flex items-center space-x-3 px-4 py-3 text-sm transition-colors ${
                    activeSection === section.id
                      ? 'bg-blue-50 text-blue-600 font-medium'
                      : 'text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{section.label}</span>
                  <ChevronRight className="h-4 w-4 ml-auto text-gray-400" />
                </button>
              )
            })}
          </nav>
        </div>
        
        <div className="flex-1">
          <div className="bg-white rounded-xl border border-gray-200">
            {activeSection === 'profile' && (
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-6">个人资料</h3>
                <div className="flex items-center space-x-6 mb-8">
                  <div className="relative">
                    <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
                      <span className="text-2xl font-bold text-white">李</span>
                    </div>
                    <button className="absolute bottom-0 right-0 p-1.5 bg-white rounded-full shadow-md border border-gray-200">
                      <Camera className="h-4 w-4 text-gray-600" />
                    </button>
                  </div>
                  <div>
                    <h4 className="text-lg font-medium text-gray-900">{profile.name}</h4>
                    <p className="text-sm text-gray-500">数学教师 · 高三年级</p>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">姓名</label>
                    <input
                      type="text"
                      value={profile.name}
                      onChange={(e) => setProfile(prev => ({ ...prev, name: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">工号</label>
                    <input type="text" defaultValue="T2024001" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50" disabled />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      <Mail className="h-4 w-4 inline mr-1" />
                      邮箱
                    </label>
                    <input
                      type="email"
                      value={profile.email}
                      onChange={(e) => setProfile(prev => ({ ...prev, email: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      <Phone className="h-4 w-4 inline mr-1" />
                      手机号
                    </label>
                    <input
                      type="tel"
                      value={profile.phone}
                      onChange={(e) => setProfile(prev => ({ ...prev, phone: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">任教学科</label>
                    <input type="text" defaultValue="数学" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50" disabled />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">任教年级</label>
                    <input type="text" defaultValue="高三" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50" disabled />
                  </div>
                </div>
                
                <div className="mt-6 flex justify-end">
                  <button
                    onClick={handleSaveProfile}
                    className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
                  >
                    <Save className="h-4 w-4 mr-2" />
                    保存修改
                  </button>
                </div>
              </div>
            )}
            
            {activeSection === 'class' && (
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-gray-900">班级管理</h3>
                  <button
                    onClick={() => setShowAddClass(true)}
                    className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    新建班级
                  </button>
                </div>
                
                {showAddClass && (
                  <div className="mb-6 p-4 border-2 border-dashed border-blue-300 rounded-lg bg-blue-50">
                    <h4 className="text-sm font-medium text-gray-900 mb-4">新建班级</h4>
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">班级名称</label>
                        <input
                          type="text"
                          value={newClass.name}
                          onChange={(e) => setNewClass(prev => ({ ...prev, name: e.target.value }))}
                          placeholder="例如：高三4班"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">任教学科</label>
                        <select
                          value={newClass.subject}
                          onChange={(e) => setNewClass(prev => ({ ...prev, subject: e.target.value }))}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="数学">数学</option>
                          <option value="语文">语文</option>
                          <option value="英语">英语</option>
                          <option value="物理">物理</option>
                          <option value="化学">化学</option>
                          <option value="生物">生物</option>
                          <option value="历史">历史</option>
                          <option value="地理">地理</option>
                          <option value="政治">政治</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">学生人数</label>
                        <input
                          type="number"
                          value={newClass.students}
                          onChange={(e) => setNewClass(prev => ({ ...prev, students: parseInt(e.target.value) || 0 }))}
                          placeholder="45"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">年级</label>
                        <select
                          value={newClass.grade}
                          onChange={(e) => setNewClass(prev => ({ ...prev, grade: e.target.value }))}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="高一">高一</option>
                          <option value="高二">高二</option>
                          <option value="高三">高三</option>
                        </select>
                      </div>
                    </div>
                    <div className="flex justify-end space-x-3">
                      <button
                        onClick={() => setShowAddClass(false)}
                        className="px-4 py-2.5 border border-gray-300 rounded-xl text-sm text-gray-600 hover:bg-gray-50 transition-colors"
                      >
                        取消
                      </button>
                      <button
                        onClick={handleAddClass}
                        className="px-4 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors"
                      >
                        确认创建
                      </button>
                    </div>
                  </div>
                )}
                
                <div className="space-y-3">
                  {classes.map((cls) => (
                    <div key={cls.id} className="flex items-center justify-between p-4 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">
                      {editingClass === cls.id ? (
                        <div className="flex-1 flex items-center space-x-4">
                          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                            <School className="h-5 w-5 text-blue-600" />
                          </div>
                          <div className="flex-1 grid grid-cols-4 gap-3">
                            <input
                              type="text"
                              value={editForm.name}
                              onChange={(e) => setEditForm(prev => ({ ...prev, name: e.target.value }))}
                              className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                              placeholder="班级名称"
                            />
                            <select
                              value={editForm.subject}
                              onChange={(e) => setEditForm(prev => ({ ...prev, subject: e.target.value }))}
                              className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            >
                              <option value="数学">数学</option>
                              <option value="语文">语文</option>
                              <option value="英语">英语</option>
                              <option value="物理">物理</option>
                              <option value="化学">化学</option>
                              <option value="生物">生物</option>
                              <option value="历史">历史</option>
                              <option value="地理">地理</option>
                              <option value="政治">政治</option>
                            </select>
                            <input
                              type="number"
                              value={editForm.students}
                              onChange={(e) => setEditForm(prev => ({ ...prev, students: parseInt(e.target.value) || 0 }))}
                              className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                              placeholder="人数"
                            />
                            <select
                              value={editForm.grade}
                              onChange={(e) => setEditForm(prev => ({ ...prev, grade: e.target.value }))}
                              className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            >
                              <option value="高一">高一</option>
                              <option value="高二">高二</option>
                              <option value="高三">高三</option>
                            </select>
                          </div>
                          <div className="flex items-center space-x-2">
                            <button onClick={handleSaveEdit} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors">保存</button>
                            <button onClick={() => setEditingClass(null)} className="p-1.5 text-gray-400 hover:text-gray-600 rounded-xl hover:bg-gray-100 transition-colors"><X className="h-4 w-4" /></button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="flex items-center space-x-4">
                            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                              <School className="h-5 w-5 text-blue-600" />
                            </div>
                            <div>
                              <p className="text-sm font-medium text-gray-900">{cls.name}</p>
                              <p className="text-xs text-gray-500">{cls.subject} · {cls.students}名学生 · {cls.grade}</p>
                            </div>
                          </div>
                          <div className="flex items-center space-x-2">
                            <button
                              onClick={() => handleEditClass(cls)}
                              className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-xl flex items-center space-x-1 transition-colors"
                            >
                              <Edit className="h-3.5 w-3.5" />
                              <span>编辑</span>
                            </button>
                            <button
                              onClick={() => handleDeleteClass(cls.id)}
                              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-colors"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {activeSection === 'notification' && (
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-6">通知设置</h3>
                <div className="space-y-4">
                  {[
                    { key: 'email', label: '邮件通知', desc: '接收作业批改完成、成绩分析等邮件通知' },
                    { key: 'browser', label: '浏览器通知', desc: '在浏览器中显示实时通知提醒' },
                    { key: 'homework', label: '作业提醒', desc: '作业批改完成后发送提醒' },
                    { key: 'alert', label: '预警通知', desc: '学生成绩异常时发送预警通知' },
                  ].map((item) => (
                    <div key={item.key} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{item.label}</p>
                        <p className="text-xs text-gray-500">{item.desc}</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={notifications[item.key]}
                          onChange={(e) => setNotifications(prev => ({ ...prev, [item.key]: e.target.checked }))}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {activeSection === 'appearance' && (
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-6">外观设置</h3>
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-3">主题模式</p>
                  <div className="grid grid-cols-3 gap-3">
                    {[
                      { id: 'light', label: '浅色', icon: Sun },
                      { id: 'dark', label: '深色', icon: Moon },
                      { id: 'system', label: '跟随系统', icon: Monitor },
                    ].map((t) => {
                      const Icon = t.icon
                      return (
                        <button
                          key={t.id}
                          onClick={() => setTheme(t.id)}
                          className={`p-4 rounded-lg border-2 text-center transition-all ${
                            theme === t.id
                              ? 'border-blue-500 bg-blue-50'
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                        >
                          <Icon className={`h-6 w-6 mx-auto mb-2 ${theme === t.id ? 'text-blue-600' : 'text-gray-400'}`} />
                          <span className={`text-sm ${theme === t.id ? 'text-blue-600 font-medium' : 'text-gray-600'}`}>{t.label}</span>
                        </button>
                      )
                    })}
                  </div>
                </div>
              </div>
            )}
            
            {activeSection === 'security' && (
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-6">安全设置</h3>
                <div className="space-y-4">
                  <div className="p-4 border border-gray-200 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">修改密码</p>
                        <p className="text-xs text-gray-500">定期修改密码以保障账户安全</p>
                      </div>
                      <button
                        onClick={() => setShowPasswordModal(true)}
                        className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
                      >
                        <Key className="h-4 w-4 mr-2" />
                        修改
                      </button>
                    </div>
                  </div>
                  <div className="p-4 border border-gray-200 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">登录设备管理</p>
                        <p className="text-xs text-gray-500">查看和管理已登录的设备</p>
                      </div>
                      <button className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50">
                        查看
                      </button>
                    </div>
                  </div>
                </div>
                
                {showPasswordModal && (
                  <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[100] flex items-center justify-center">
                    <div className="bg-white rounded-2xl shadow-2xl p-6 w-96 animate-scale-in">
                      <div className="flex items-center justify-between mb-4">
                        <h4 className="text-lg font-semibold">修改密码</h4>
                        <button onClick={() => setShowPasswordModal(false)} className="p-1 hover:bg-gray-100 rounded-full">
                          <X className="h-5 w-5" />
                        </button>
                      </div>
                      <div className="space-y-3">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">当前密码</label>
                          <input
                            type="password"
                            value={passwordForm.old}
                            onChange={(e) => setPasswordForm(prev => ({ ...prev, old: e.target.value }))}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            placeholder="请输入当前密码"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">新密码</label>
                          <input
                            type="password"
                            value={passwordForm.new}
                            onChange={(e) => setPasswordForm(prev => ({ ...prev, new: e.target.value }))}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            placeholder="请输入新密码（至少6位）"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">确认新密码</label>
                          <input
                            type="password"
                            value={passwordForm.confirm}
                            onChange={(e) => setPasswordForm(prev => ({ ...prev, confirm: e.target.value }))}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            placeholder="请再次输入新密码"
                          />
                        </div>
                      </div>
                      <div className="flex justify-end space-x-3 mt-6">
                        <button
                          onClick={() => setShowPasswordModal(false)}
                          className="px-4 py-2.5 border border-gray-300 rounded-xl text-sm text-gray-600 hover:bg-gray-50 transition-colors"
                        >
                          取消
                        </button>
                        <button
                          onClick={handleChangePassword}
                          className="px-4 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors"
                        >
                          确认修改
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {activeSection === 'data' && (
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-6">数据管理</h3>
                <div className="space-y-4">
                  <div className="p-4 border border-gray-200 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">导出数据</p>
                        <p className="text-xs text-gray-500">导出班级数据、成绩记录等</p>
                      </div>
                      <button
                        onClick={handleExportData}
                        className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
                      >
                        <Download className="h-4 w-4 mr-2" />
                        导出
                      </button>
                    </div>
                  </div>
                  <div className="p-4 border border-gray-200 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">清除缓存</p>
                        <p className="text-xs text-gray-500">清除本地缓存数据以释放空间</p>
                      </div>
                      <button
                        onClick={handleClearCache}
                        className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        清除
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
      
      <ConfirmDialog
        isOpen={showDeleteConfirm}
        title="删除班级"
        message="删除后该班级的所有数据将无法恢复，确定要删除吗？"
        onConfirm={confirmDelete}
        onCancel={() => { setShowDeleteConfirm(false); setDeleteTargetId(null) }}
        confirmText="确认删除"
        cancelText="再想想"
      />
    </div>
  )
}

export default Settings
