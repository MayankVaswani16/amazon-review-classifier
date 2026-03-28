import { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import { FiTrendingUp, FiThumbsUp, FiThumbsDown, FiTarget } from 'react-icons/fi'
import { getStats, getTsneBefore, getTsneAfter } from '../api/client'
import Spinner from '../components/Spinner'

const COLORS = {
  positive: '#22c55e',
  negative: '#ef4444',
  primary: '#6366f1',
  accent: '#d946ef',
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const res = await getStats()
      setStats(res.data)
    } catch (err) {
      toast.error('Failed to load statistics')
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <Spinner size="lg" text="Loading dashboard..." />

  if (!stats) {
    return (
      <div className="page-container text-center text-dark-400 py-20">
        <p className="text-xl">No data available yet.</p>
        <p className="text-sm mt-2">Analyze some reviews first to see statistics here.</p>
      </div>
    )
  }

  const donutData = [
    { name: 'Positive', value: stats.positivePredictions },
    { name: 'Negative', value: stats.negativePredictions },
  ]

  const nounData = (stats.topNouns || []).map(n => ({ name: n.word, count: n.count }))
  const adjData = (stats.topAdjectives || []).map(a => ({ name: a.word, count: a.count }))

  // SMOTE distribution data
  const smoteBefore = stats.smoteDistribution?.before || {}
  const smoteAfter = stats.smoteDistribution?.after || {}
  const smoteData = Object.keys(smoteBefore).length > 0 ? [
    {
      name: 'Before SMOTE',
      Negative: smoteBefore['0'] || 0,
      Positive: smoteBefore['1'] || 0,
    },
    {
      name: 'After SMOTE',
      Negative: smoteAfter['0'] || 0,
      Positive: smoteAfter['1'] || 0,
    },
  ] : []

  return (
    <div className="page-container space-y-8 animate-fade-in">
      <h1 className="section-title text-3xl">Dashboard</h1>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={FiTrendingUp}
          label="Total Predictions"
          value={stats.totalPredictions}
          color="text-primary-400"
          bgColor="bg-primary-500/10"
        />
        <StatCard
          icon={FiThumbsUp}
          label="Positive"
          value={stats.positivePredictions}
          color="text-emerald-400"
          bgColor="bg-emerald-500/10"
        />
        <StatCard
          icon={FiThumbsDown}
          label="Negative"
          value={stats.negativePredictions}
          color="text-red-400"
          bgColor="bg-red-500/10"
        />
        <StatCard
          icon={FiTarget}
          label="Avg Confidence"
          value={`${(stats.averageConfidence * 100).toFixed(1)}%`}
          color="text-accent-400"
          bgColor="bg-accent-500/10"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Donut Chart */}
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-lg font-semibold text-white">Sentiment Distribution</h3>
          {stats.totalPredictions > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={donutData}
                  cx="50%"
                  cy="50%"
                  innerRadius={70}
                  outerRadius={110}
                  paddingAngle={4}
                  dataKey="value"
                >
                  <Cell fill={COLORS.positive} />
                  <Cell fill={COLORS.negative} />
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '12px',
                    color: '#f8fafc',
                  }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-dark-500 text-center py-20">No predictions yet</p>
          )}
        </div>

        {/* SMOTE Bar Chart */}
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-lg font-semibold text-white">SMOTE Class Distribution</h3>
          {smoteData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={smoteData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    background: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '12px',
                    color: '#f8fafc',
                  }}
                />
                <Legend />
                <Bar dataKey="Negative" fill={COLORS.negative} radius={[4, 4, 0, 0]} />
                <Bar dataKey="Positive" fill={COLORS.positive} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-dark-500 text-center py-20">SMOTE data not available</p>
          )}
        </div>
      </div>

      {/* Bar Charts: Nouns & Adjectives */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Nouns */}
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-lg font-semibold text-white">Top Product Features (Nouns)</h3>
          {nounData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={nounData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis type="number" stroke="#94a3b8" fontSize={12} />
                <YAxis type="category" dataKey="name" width={80} stroke="#94a3b8" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    background: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '12px',
                    color: '#f8fafc',
                  }}
                />
                <Bar dataKey="count" fill="#38bdf8" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-dark-500 text-center py-20">No noun data yet</p>
          )}
        </div>

        {/* Top Adjectives */}
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-lg font-semibold text-white">Top Sentiment Descriptors (Adjectives)</h3>
          {adjData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={adjData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis type="number" stroke="#94a3b8" fontSize={12} />
                <YAxis type="category" dataKey="name" width={80} stroke="#94a3b8" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    background: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '12px',
                    color: '#f8fafc',
                  }}
                />
                <Bar dataKey="count" fill="#a78bfa" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-dark-500 text-center py-20">No adjective data yet</p>
          )}
        </div>
      </div>

      {/* t-SNE Images */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-lg font-semibold text-white">t-SNE Before SMOTE</h3>
          <img
            src={getTsneBefore()}
            alt="t-SNE visualization before SMOTE"
            className="w-full rounded-lg bg-dark-800"
            onError={(e) => { e.target.style.display = 'none' }}
          />
        </div>
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-lg font-semibold text-white">t-SNE After SMOTE</h3>
          <img
            src={getTsneAfter()}
            alt="t-SNE visualization after SMOTE"
            className="w-full rounded-lg bg-dark-800"
            onError={(e) => { e.target.style.display = 'none' }}
          />
        </div>
      </div>
    </div>
  )
}

function StatCard({ icon: Icon, label, value, color, bgColor }) {
  return (
    <div className="stat-card group hover:border-primary-500/30 transition-all duration-300">
      <div className="flex items-center justify-between">
        <div className={`w-10 h-10 ${bgColor} rounded-xl flex items-center justify-center`}>
          <Icon className={color} size={20} />
        </div>
      </div>
      <div>
        <p className="text-2xl font-bold text-white">{value}</p>
        <p className="text-sm text-dark-400">{label}</p>
      </div>
    </div>
  )
}
