import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Analyzer from './pages/Analyzer'
import Dashboard from './pages/Dashboard'
import History from './pages/History'
import BulkUpload from './pages/BulkUpload'

function App() {
  return (
    <div className="min-h-screen bg-dark-950">
      {/* Background gradient orbs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary-600/10 rounded-full blur-3xl" />
        <div className="absolute top-1/2 -left-40 w-96 h-96 bg-accent-600/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 right-1/3 w-72 h-72 bg-primary-500/5 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10">
        <Navbar />
        <main className="pt-4">
          <Routes>
            <Route path="/" element={<Analyzer />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/history" element={<History />} />
            <Route path="/bulk" element={<BulkUpload />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default App
