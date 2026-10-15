import React, { useState } from 'react'
import { MessageSquarePlus, X } from 'lucide-react'
import { useToast } from './Toast'
import { feedbackAPI, getErrorMessage } from '../utils/api'

const TOPIC_OPTIONS = [
  '教案不符合课标或教材版本',
  '作业批改有误判 / 评分不准',
  '手写识别（OCR）不准确',
  '变式题难度或质量不合适',
  '生成速度太慢',
  '页面操作不方便',
  '其他',
]

const OTHER_TOPIC = '其他'
const MAX_CONTENT = 300
const MAX_CONTACT = 100

const FeedbackDialog = ({ isOpen, onClose }) => {
  const { addToast } = useToast()
  const [topics, setTopics] = useState([])
  const [content, setContent] = useState('')
  const [contact, setContact] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (!isOpen) return null

  const resetForm = () => {
    setTopics([])
    setContent('')
    setContact('')
  }

  const handleClose = () => {
    if (submitting) return
    resetForm()
    onClose()
  }

  const toggleTopic = (topic) => {
    setTopics((prev) =>
      prev.includes(topic) ? prev.filter((t) => t !== topic) : [...prev, topic],
    )
  }

  const canSubmit = topics.length > 0 || content.trim().length > 0

  const handleSubmit = async () => {
    if (!canSubmit || submitting) return

    if (topics.includes(OTHER_TOPIC) && !content.trim()) {
      addToast('选择「其他」时，请填写具体意见', 'error')
      return
    }

    setSubmitting(true)
    try {
      await feedbackAPI.submit({
        topics,
        content: content.trim().slice(0, MAX_CONTENT),
        contact: contact.trim().slice(0, MAX_CONTACT),
        page: window.location.pathname || '',
      })
      addToast('感谢反馈，我们会认真改进', 'success')
      resetForm()
      onClose()
    } catch (err) {
      addToast(getErrorMessage(err), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={handleClose} />
      <div className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl p-6 animate-scale-in">
        <button
          type="button"
          onClick={handleClose}
          disabled={submitting}
          className="absolute top-4 right-4 p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full disabled:opacity-50"
          aria-label="关闭"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="flex items-center mb-4 pr-8">
          <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center mr-3">
            <MessageSquarePlus className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">意见反馈</h3>
            <p className="text-sm text-gray-500">您的建议能帮助我们做得更好</p>
          </div>
        </div>

        <fieldset className="mb-4">
          <legend className="text-sm font-medium text-gray-700 mb-2">
            您遇到了哪些问题？（可多选）
          </legend>
          <div className="space-y-2">
            {TOPIC_OPTIONS.map((topic) => {
              const checked = topics.includes(topic)
              return (
                <label
                  key={topic}
                  className={`flex items-start gap-2.5 rounded-xl border px-3 py-2.5 text-sm cursor-pointer transition-colors ${
                    checked
                      ? 'border-blue-300 bg-blue-50 text-blue-800'
                      : 'border-gray-200 text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleTopic(topic)}
                    disabled={submitting}
                    className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span>{topic}</span>
                </label>
              )
            })}
          </div>
        </fieldset>

        <div className="mb-4">
          <label htmlFor="feedback-content" className="block text-sm font-medium text-gray-700 mb-2">
            还有什么想告诉我们的？（选填，{MAX_CONTENT} 字以内）
          </label>
          <textarea
            id="feedback-content"
            value={content}
            onChange={(e) => setContent(e.target.value.slice(0, MAX_CONTENT))}
            disabled={submitting}
            rows={4}
            placeholder="请尽量具体描述，方便我们排查和改进"
            className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm text-gray-800 placeholder:text-gray-400 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100 disabled:bg-gray-50 resize-none"
          />
          <div className="mt-1 text-right text-xs text-gray-400">
            {content.length}/{MAX_CONTENT}
          </div>
        </div>

        <div className="mb-5">
          <label htmlFor="feedback-contact" className="block text-sm font-medium text-gray-700 mb-2">
            联系方式（选填）
          </label>
          <input
            id="feedback-contact"
            type="text"
            value={contact}
            onChange={(e) => setContact(e.target.value.slice(0, MAX_CONTACT))}
            disabled={submitting}
            maxLength={MAX_CONTACT}
            placeholder="微信或手机号，方便我们回访（选填）"
            className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm text-gray-800 placeholder:text-gray-400 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100 disabled:bg-gray-50"
          />
        </div>

        <div className="flex space-x-3">
          <button
            type="button"
            onClick={handleClose}
            disabled={submitting}
            className="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl text-sm text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            取消
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!canSubmit || submitting}
            className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? '提交中…' : '提交'}
          </button>
        </div>
      </div>
      <style>{`
        @keyframes scale-in {
          from { opacity: 0; transform: scale(0.9); }
          to { opacity: 1; transform: scale(1); }
        }
        .animate-scale-in {
          animation: scale-in 0.2s ease-out;
        }
      `}</style>
    </div>
  )
}

export default FeedbackDialog
