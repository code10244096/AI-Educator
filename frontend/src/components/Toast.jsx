import React, { useState, useCallback } from 'react'
import { CheckCircle, AlertCircle, X, Info } from 'lucide-react'

const ToastContext = React.createContext()

export const useToast = () => {
  const context = React.useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return context
}

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((message, type = 'success') => {
    const id = Date.now()
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 3000)
  }, [])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <div className="fixed top-20 left-1/2 -translate-x-1/2 z-[100] space-y-3">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`flex items-center space-x-3 px-5 py-3 rounded-xl shadow-lg border backdrop-blur-sm animate-slide-in ${
              toast.type === 'success'
                ? 'bg-green-50/95 border-green-200 text-green-800'
                : toast.type === 'error'
                ? 'bg-red-50/95 border-red-200 text-red-800'
                : 'bg-blue-50/95 border-blue-200 text-blue-800'
            }`}
          >
            {toast.type === 'success' && <CheckCircle className="h-5 w-5 text-green-500" />}
            {toast.type === 'error' && <AlertCircle className="h-5 w-5 text-red-500" />}
            {toast.type === 'info' && <Info className="h-5 w-5 text-blue-500" />}
            <span className="text-sm font-medium">{toast.message}</span>
            <button onClick={() => removeToast(toast.id)} className="ml-2 p-1 hover:bg-white/50 rounded-full">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
      <style>{`
        @keyframes slide-in {
          from { opacity: 0; transform: translateY(-20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-slide-in {
          animation: slide-in 0.3s ease-out;
        }
      `}</style>
    </ToastContext.Provider>
  )
}
