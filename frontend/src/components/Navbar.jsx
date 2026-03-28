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
    <nav className="sticky top-0 z-50 glass-card border-t-0 rounded-t-none border-x-0">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <NavLink to="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center
                            shadow-lg shadow-primary-500/25 group-hover:shadow-primary-500/40 transition-shadow duration-300">
              <span className="text-white font-bold text-sm">SC</span>
            </div>
            <span className="text-lg font-bold bg-gradient-to-r from-primary-400 to-accent-400 bg-clip-text text-transparent
                             hidden sm:block">
              Sentiment Classifier
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
                    ? 'bg-primary-500/20 text-primary-400 shadow-lg shadow-primary-500/10'
                    : 'text-dark-300 hover:text-white hover:bg-dark-800/50'
                  }`
                }
              >
                <Icon size={16} />
                {label}
              </NavLink>
            ))}
          </div>

          {/* Mobile menu button */}
          <button
            className="md:hidden p-2 rounded-lg text-dark-300 hover:text-white hover:bg-dark-800/50 transition-colors"
            onClick={() => setOpen(!open)}
            id="mobile-menu-button"
          >
            {open ? <HiOutlineX size={24} /> : <HiOutlineMenu size={24} />}
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
                    ? 'bg-primary-500/20 text-primary-400'
                    : 'text-dark-300 hover:text-white hover:bg-dark-800/50'
                  }`
                }
              >
                <Icon size={18} />
                {label}
              </NavLink>
            ))}
          </div>
        )}
      </div>
    </nav>
  )
}
