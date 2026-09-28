import React, { useEffect, useState } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Users,
  FileCheck,
  BookOpen,
  FileText,
  Settings,
  BarChart3,
  ChevronDown,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Plus,
} from 'lucide-react'
import { useLayout } from '../context/LayoutContext'
import { useClass } from '../context/ClassContext'
import { useAuth } from '../context/AuthContext'

// 教师菜单（R1-006）：工作台 / 我的班级 / 作业批改 / 错题本 / 教案 ── 设置；用量统计仅管理员可见
const MAIN_ITEMS = [
  { id: 'home', label: '工作台', icon: LayoutDashboard, path: '/', exact: true },
  { id: 'classes', label: '我的班级', icon: Users, path: '/class' },
  { id: 'grader', label: '作业批改', icon: FileCheck, path: '/grader' },
  { id: 'notebook', label: '错题本', icon: BookOpen, path: '/notebook' },
  { id: 'lessonplan', label: '教案', icon: FileText, path: '/lessonplan' },
]

const itemClass = (active, collapsed) => [
  'group flex w-full items-center rounded-lg text-sm transition-colors',
  collapsed ? 'justify-center px-0 py-2.5' : 'px-3 py-2.5',
  active ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
].join(' ')

const iconClass = (active) => `h-[18px] w-[18px] flex-shrink-0 ${active ? 'text-blue-600' : 'text-gray-400 group-hover:text-gray-600'}`

const classPathMatches = (pathname, cls) => {
  const ids = [String(cls.id), cls.slug].filter(Boolean)
  return ids.some(id => pathname === `/class/${id}` || pathname.startsWith(`/class/${id}/`))
}

const Sidebar = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { pathname } = location
  const { sidebarOpen, closeSidebar, collapsed, toggleCollapsed } = useLayout()
  const { classes } = useClass()
  const { isAdmin } = useAuth()
  const [classesExpanded, setClassesExpanded] = useState(true)

  // 窄屏抽屉：切换页面后自动收起（桌面常驻不受影响）
  useEffect(() => {
    closeSidebar()
  }, [pathname, closeSidebar])

  const isActive = (item) => (item.exact ? pathname === item.path : pathname === item.path || pathname.startsWith(`${item.path}/`))

  // 窄屏抽屉里总是完整显示；只有桌面才折叠成图标栏
  const renderNav = (isCollapsed) => (
    <nav className="flex h-full flex-col" aria-label="主菜单">
      <div className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {MAIN_ITEMS.map((item) => {
          const Icon = item.icon
          const active = isActive(item)
          if (item.id !== 'classes') {
            return (
              <NavLink
                key={item.id}
                to={item.path}
                end={item.exact}
                title={isCollapsed ? item.label : undefined}
                className={itemClass(active, isCollapsed)}
                aria-current={active ? 'page' : undefined}
              >
                <Icon className={iconClass(active)} />
                {!isCollapsed && <span className="ml-3 truncate">{item.label}</span>}
              </NavLink>
            )
          }

          // 我的班级：点父级进入班级列表；子项为各班，末尾“新建班级”
          const parentActive = pathname === '/class'
          const sectionActive = active
          return (
            <div key={item.id}>
              <div
                className={`group flex w-full items-center rounded-lg text-sm transition-colors ${
                  parentActive
                    ? 'bg-blue-50 font-medium text-blue-700'
                    : sectionActive ? 'text-blue-700 hover:bg-gray-100' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`}
              >
                <NavLink
                  to="/class"
                  end
                  title={isCollapsed ? item.label : undefined}
                  className={`flex min-w-0 flex-1 items-center ${isCollapsed ? 'justify-center py-2.5' : 'py-2.5 pl-3'}`}
                  aria-current={parentActive ? 'page' : undefined}
                >
                  <Icon className={iconClass(sectionActive)} />
                  {!isCollapsed && <span className="ml-3 truncate">{item.label}</span>}
                </NavLink>
                {!isCollapsed && (
                  <button
                    type="button"
                    onClick={() => setClassesExpanded(v => !v)}
                    className="mr-1 rounded p-1.5 text-gray-400 hover:bg-gray-200 hover:text-gray-600"
                    aria-label={classesExpanded ? '收起班级列表' : '展开班级列表'}
                    aria-expanded={classesExpanded}
                  >
                    {classesExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  </button>
                )}
              </div>
              {!isCollapsed && classesExpanded && (
                <div className="mt-1 space-y-0.5 pl-9">
                  {classes.map((cls) => {
                    const childActive = classPathMatches(pathname, cls)
                    return (
                      <NavLink
                        key={cls.id}
                        to={`/class/${cls.id}`}
                        className={`block truncate rounded-lg px-3 py-2 text-sm ${
                          childActive ? 'bg-blue-50 font-medium text-blue-700' : 'text-gray-500 hover:bg-gray-100 hover:text-gray-800'
                        }`}
                        aria-current={childActive ? 'page' : undefined}
                        title={cls.name}
                      >
                        {cls.name}
                      </NavLink>
                    )
                  })}
                  <button
                    type="button"
                    onClick={() => navigate('/class?create=1')}
                    className="flex w-full items-center rounded-lg px-3 py-2 text-sm text-blue-600 hover:bg-blue-50"
                  >
                    <Plus className="mr-1.5 h-4 w-4" />
                    新建班级
                  </button>
                </div>
              )}
            </div>
          )
        })}

        <div className="my-3 border-t border-gray-100" role="separator" />

        <NavLink
          to="/settings"
          title={isCollapsed ? '设置' : undefined}
          className={itemClass(pathname.startsWith('/settings'), isCollapsed)}
        >
          <Settings className={iconClass(pathname.startsWith('/settings'))} />
          {!isCollapsed && <span className="ml-3">设置</span>}
        </NavLink>

        {/* 运维功能：仅管理员（isAdmin）可见 */}
        {isAdmin && (
          <NavLink
            to="/usage"
            title={isCollapsed ? '用量统计' : undefined}
            className={itemClass(pathname.startsWith('/usage'), isCollapsed)}
          >
            <BarChart3 className={iconClass(pathname.startsWith('/usage'))} />
            {!isCollapsed && <span className="ml-3">用量统计</span>}
          </NavLink>
        )}
      </div>
    </nav>
  )

  return (
    <>
      {/* 桌面（≥1024px）：常驻侧栏，可折叠为 64px 图标栏 */}
      <aside
        className={`fixed bottom-0 left-0 top-16 z-30 hidden flex-col border-r border-gray-200 bg-white lg:flex ${
          collapsed ? 'w-16' : 'w-[232px]'
        }`}
      >
        <div className="min-h-0 flex-1">{renderNav(collapsed)}</div>
        <button
          type="button"
          onClick={toggleCollapsed}
          className={`flex items-center border-t border-gray-100 py-3 text-sm text-gray-400 hover:bg-gray-50 hover:text-gray-600 ${
            collapsed ? 'justify-center' : 'px-6'
          }`}
          aria-label={collapsed ? '展开侧栏' : '收起侧栏'}
          title={collapsed ? '展开侧栏' : '收起侧栏'}
        >
          {collapsed ? <ChevronsRight className="h-4 w-4" /> : <><ChevronsLeft className="mr-2 h-4 w-4" />收起</>}
        </button>
      </aside>

      {/* 窄屏（<1024px）：抽屉 */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/30 lg:hidden" onClick={closeSidebar} aria-hidden="true" />
      )}
      <aside
        className={`fixed bottom-0 left-0 top-16 z-50 w-64 max-w-[80vw] border-r border-gray-200 bg-white transition-transform duration-200 lg:hidden ${
          sidebarOpen ? 'translate-x-0' : 'invisible -translate-x-full'
        }`}
        aria-hidden={!sidebarOpen}
      >
        {renderNav(false)}
      </aside>
    </>
  )
}

export default Sidebar
