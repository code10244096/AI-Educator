import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  FileCheck,
  FileText,
  Users,
  FolderOpen,
  CheckSquare,
  Settings,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  Archive,
  Database,
  BookOpen,
  BrainCircuit,
  Upload,
  Search,
  GraduationCap,
  Plus,
  X
} from 'lucide-react'
import { useLayout } from '../context/LayoutContext'
import { useClass } from '../context/ClassContext'

const SidebarItem = ({ icon: Icon, label, path, isActive, onClick, hasChildren, isExpanded, children }) => {
  return (
    <div>
      <button
        onClick={onClick}
        className={`w-full flex items-center justify-between px-4 py-2.5 text-sm transition-all duration-200 rounded-lg mx-2 ${
          isActive
            ? 'bg-blue-500/10 text-blue-600 font-medium'
            : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
        }`}
      >
        <div className="flex items-center space-x-3">
          <Icon className={`h-4 w-4 ${isActive ? 'text-blue-600' : 'text-gray-400'}`} />
          <span>{label}</span>
        </div>
        {hasChildren && (
          isExpanded ? (
            <ChevronDown className="h-4 w-4 text-gray-400" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-400" />
          )
        )}
      </button>
      {hasChildren && isExpanded && (
        <div className="ml-8 mt-1 space-y-1">
          {children}
        </div>
      )}
    </div>
  )
}

const SidebarChildItem = ({ icon: Icon, label, path, isActive, onClick }) => {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center space-x-3 px-4 py-2 text-sm transition-all duration-200 rounded-lg ${
        isActive
          ? 'bg-blue-500/10 text-blue-600 font-medium'
          : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
      }`}
    >
      <Icon className={`h-3.5 w-3.5 ${isActive ? 'text-blue-600' : 'text-gray-400'}`} />
      <span>{label}</span>
    </button>
  )
}

const Sidebar = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { sidebarOpen, closeSidebar } = useLayout()
  const { classes } = useClass()
  const [expandedMenus, setExpandedMenus] = useState({
    myClasses: true,
    questionBank: false,
  })

  const toggleMenu = (key) => {
    setExpandedMenus(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const isActive = (path) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  const classItems = classes.map(cls => ({
    label: cls.name,
    icon: GraduationCap,
    path: `/class/class${cls.id}`,
  }))

  const menuItems = [
    {
      id: 'grader',
      label: '作业批改',
      icon: FileCheck,
      path: '/grader',
    },
    {
      id: 'lessonplan',
      label: '教案生成',
      icon: FileText,
      path: '/lessonplan',
    },
    {
      id: 'myClasses',
      label: '我的班级',
      icon: Users,
      path: '/class',
      hasChildren: true,
      children: classItems,
    },
    {
      id: 'questionBank',
      label: '题库管理',
      icon: FolderOpen,
      path: '/questionbank',
      hasChildren: true,
      children: [
        { label: '我的题库', icon: Upload, path: '/questionbank/my' },
        { label: '真题资源库', icon: Database, path: '/questionbank/real' },
        { label: 'AI 智题库', icon: BrainCircuit, path: '/questionbank/ai' },
      ],
    },
    {
      id: 'tasks',
      label: '我的任务',
      icon: CheckSquare,
      path: '/tasks',
    },
    {
      id: 'settings',
      label: '设置',
      icon: Settings,
      path: '/settings',
    },
  ]

  return (
    <>
      {/* Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-40 transition-opacity"
          onClick={closeSidebar}
        />
      )}
      
      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-16 bottom-0 w-64 bg-white border-r border-gray-200 overflow-y-auto z-50 transition-transform duration-300 ease-in-out ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <nav className="py-4">
          {menuItems.map((item) => {
            const Icon = item.icon
            const itemActive = isActive(item.path)
            
            if (item.hasChildren) {
              const isExpanded = expandedMenus[item.id]
              return (
                <SidebarItem
                  key={item.id}
                  icon={Icon}
                  label={item.label}
                  isActive={itemActive}
                  hasChildren={true}
                  isExpanded={isExpanded}
                  onClick={() => {
                    toggleMenu(item.id)
                    if (!isExpanded && item.children.length > 0) {
                      navigate(item.children[0].path)
                    }
                  }}
                >
                  {item.children.map((child) => {
                    const ChildIcon = child.icon
                    const childActive = isActive(child.path)
                    return (
                      <SidebarChildItem
                        key={child.path}
                        icon={ChildIcon}
                        label={child.label}
                        path={child.path}
                        isActive={childActive}
                        onClick={() => {
                          navigate(child.path)
                          closeSidebar()
                        }}
                      />
                    )
                  })}
                </SidebarItem>
              )
            }

            return (
              <SidebarItem
                key={item.id}
                icon={Icon}
                label={item.label}
                path={item.path}
                isActive={itemActive}
                onClick={() => {
                  navigate(item.path)
                  closeSidebar()
                }}
              />
            )
          })}
        </nav>
      </aside>
    </>
  )
}

export default Sidebar
