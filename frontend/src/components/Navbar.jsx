import { NavLink } from 'react-router-dom'
import { useState } from 'react'
import { HiOutlineMenu, HiOutlineX } from 'react-icons/hi'
import { FiActivity, FiBarChart2, FiClock, FiUploadCloud } from 'react-icons/fi'

const navItems = [
  { to: '/', label: 'Analyzer', icon: FiActivity },
  { to: '/dashboard', label: 'Dashboard', icon: FiBarChart2 },
  { to: '/history', label: 'History', icon: FiClock },
  { to: '/bulk', label: 'Bulk Upload', icon: FiUploadCloud },
]

export default function Navbar() {
  const [open, setOpen] = useState(false)

  return (
    <nav className="sticky top-0 z-50 nav-glass">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <NavLink to="/" className="flex items-center gap-3 group">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center"
                 style={{ background: 'linear-gradient(135deg, #8083ff, #6366f1)' }}>
              <span className="text-white font-bold text-xs tracking-tight">SQ</span>
            </div>
            <span className="text-base font-semibold hidden sm:block"
                  style={{ color: '#c0c1ff', letterSpacing: '-0.02em' }}>
              SentimentIQ
            </span>
          </NavLink>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-1">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200
                  ${isActive
                    ? 'text-white'
                    : 'text-[#908fa0] hover:text-[#c7c4d7] hover:bg-white/[0.04]'
                  }`
                }
                style={({ isActive }) =>
                  isActive
                    ? { background: 'rgba(99, 102, 241, 0.12)', color: '#c0c1ff' }
                    : {}
                }
              >
                <Icon size={15} strokeWidth={2} />
                {label}
              </NavLink>
            ))}
          </div>

          {/* Mobile menu button */}
          <button
            className="md:hidden p-2 rounded-lg transition-colors"
            style={{ color: '#908fa0' }}
            onClick={() => setOpen(!open)}
            id="mobile-menu-button"
          >
            {open ? <HiOutlineX size={22} /> : <HiOutlineMenu size={22} />}
          </button>
        </div>

        {/* Mobile nav */}
        {open && (
          <div className="md:hidden pb-4 space-y-1 animate-fade-in">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200
                  ${isActive
                    ? 'text-[#c0c1ff]'
                    : 'text-[#908fa0] hover:text-[#c7c4d7] hover:bg-white/[0.04]'
                  }`
                }
                style={({ isActive }) =>
                  isActive
                    ? { background: 'rgba(99, 102, 241, 0.12)' }
                    : {}
                }
              >
                <Icon size={17} strokeWidth={2} />
                {label}
              </NavLink>
            ))}
          </div>
        )}
      </div>
    </nav>
  )
}
