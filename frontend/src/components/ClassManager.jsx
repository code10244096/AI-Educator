import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { School, Plus, Edit, Trash2, X, Users } from 'lucide-react'
import { useClass } from '../context/ClassContext'
import { useToast } from './Toast'
import ConfirmDialog from './ConfirmDialog'
import { Empty, ErrorState, Loading } from './PageState'
import { getErrorMessage } from '../utils/api'

const GRADES = ['高一', '高二', '高三']

// 班级的新建 / 编辑 / 删除（只做高中数学，学科固定为数学）
const ClassManager = ({ autoOpenCreate = false }) => {
  const navigate = useNavigate()
  const { classes, loaded, loadError, reloadClasses, addClass, updateClass, deleteClass } = useClass()
  const { addToast } = useToast()
  const [showAdd, setShowAdd] = useState(autoOpenCreate)
  const [newClass, setNewClass] = useState({ name: '', grade: '高一' })
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState({ name: '', grade: '高一' })
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [saving, setSaving] = useState(false)

  const handleAdd = async () => {
    if (!newClass.name.trim()) {
      addToast('请输入班级名称', 'error')
      return
    }
    setSaving(true)
    try {
      const created = await addClass({ name: newClass.name.trim(), grade: newClass.grade, subject: '数学' })
      setNewClass({ name: '', grade: newClass.grade })
      setShowAdd(false)
      addToast('班级已创建，下一步导入学生名单', 'success')
      navigate(`/class/${created.id}/members`)
    } catch (err) {
      addToast(getErrorMessage(err, '班级创建失败'), 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveEdit = async () => {
    if (!editForm.name.trim()) {
      addToast('请输入班级名称', 'error')
      return
    }
    setSaving(true)
    try {
      await updateClass(editingId, { name: editForm.name.trim(), grade: editForm.grade, subject: '数学' })
      setEditingId(null)
      addToast('班级信息已更新', 'success')
    } catch (err) {
      addToast(getErrorMessage(err, '保存失败'), 'error')
    } finally {
      setSaving(false)
    }
  }

  const confirmDelete = async () => {
    try {
      await deleteClass(deleteTarget.id)
      addToast('班级已删除', 'success')
    } catch (err) {
      addToast(getErrorMessage(err, '删除失败'), 'error')
    } finally {
      setDeleteTarget(null)
    }
  }

  const inputClass = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500'

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500">{loaded ? `共 ${classes.length} 个班级` : ''}</p>
        <button
          onClick={() => setShowAdd(true)}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
        >
          <Plus className="h-4 w-4 mr-1.5" />
          新建班级
        </button>
      </div>

      {showAdd && (
        <div className="mb-4 p-4 border border-blue-200 rounded-xl bg-blue-50">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1" htmlFor="new-class-name">班级名称</label>
              <input
                id="new-class-name"
                type="text"
                value={newClass.name}
                onChange={(e) => setNewClass(prev => ({ ...prev, name: e.target.value }))}
                onKeyDown={(e) => { if (e.key === 'Enter') handleAdd() }}
                placeholder="例如：高一5班"
                className={inputClass}
                autoFocus
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1" htmlFor="new-class-grade">年级</label>
              <select
                id="new-class-grade"
                value={newClass.grade}
                onChange={(e) => setNewClass(prev => ({ ...prev, grade: e.target.value }))}
                className={inputClass}
              >
                {GRADES.map(g => <option key={g} value={g}>{g}</option>)}
              </select>
            </div>
          </div>
          <div className="flex justify-end space-x-3">
            <button onClick={() => setShowAdd(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-white">
              取消
            </button>
            <button onClick={handleAdd} disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-60">
              确认创建
            </button>
          </div>
        </div>
      )}

      {loadError && <ErrorState message={loadError} onRetry={reloadClasses} compact />}
      {!loaded && !loadError && <Loading variant="skeleton" rows={3} />}
      {loaded && !loadError && classes.length === 0 && !showAdd && (
        <Empty
          icon={School}
          title="还没有班级"
          desc="新建班级后导入学生名单，就可以布置作业、上传批改了"
          action={{ label: '新建班级', onClick: () => setShowAdd(true), icon: Plus }}
        />
      )}

      <div className="space-y-3">
        {classes.map((cls) => (
          <div key={cls.id} className="flex items-center justify-between p-4 border border-gray-200 rounded-xl bg-white hover:bg-gray-50 transition-colors">
            {editingId === cls.id ? (
              <div className="flex-1 flex flex-wrap items-center gap-3">
                <input
                  type="text"
                  value={editForm.name}
                  onChange={(e) => setEditForm(prev => ({ ...prev, name: e.target.value }))}
                  className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm"
                  placeholder="班级名称"
                  aria-label="班级名称"
                />
                <select
                  value={editForm.grade}
                  onChange={(e) => setEditForm(prev => ({ ...prev, grade: e.target.value }))}
                  className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm"
                  aria-label="年级"
                >
                  {GRADES.map(g => <option key={g} value={g}>{g}</option>)}
                </select>
                <button onClick={handleSaveEdit} disabled={saving} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">保存</button>
                <button onClick={() => setEditingId(null)} className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100" aria-label="取消编辑">
                  <X className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <>
                <button className="flex items-center space-x-4 text-left min-w-0" onClick={() => navigate(`/class/${cls.id}`)}>
                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <School className="h-5 w-5 text-blue-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{cls.name}</p>
                    <p className="text-xs text-gray-500 flex items-center">
                      <Users className="h-3 w-3 mr-1" />{cls.students} 名学生 · {cls.grade}
                    </p>
                  </div>
                </button>
                <div className="flex items-center space-x-1 flex-shrink-0">
                  <button
                    onClick={() => { setEditingId(cls.id); setEditForm({ name: cls.name, grade: cls.grade || '高一' }) }}
                    className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg flex items-center space-x-1"
                  >
                    <Edit className="h-3.5 w-3.5" />
                    <span>编辑</span>
                  </button>
                  <button
                    onClick={() => setDeleteTarget(cls)}
                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                    aria-label={`删除${cls.name}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>

      <ConfirmDialog
        isOpen={!!deleteTarget}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={confirmDelete}
        title="删除班级"
        message={deleteTarget ? `确定删除「${deleteTarget.name}」吗？将同时删除该班的学生名单、全部作业和批改记录，且无法恢复（错题本里已收录的错题会保留）。` : ''}
        confirmText="确认删除"
      />
    </div>
  )
}

export default ClassManager
