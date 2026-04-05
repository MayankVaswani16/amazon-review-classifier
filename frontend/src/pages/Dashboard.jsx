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
  positive: '#4edea3',
  negative: '#ffb4ab',
  primary: '#8083ff',
  accent: '#c4b5fd',
  sky: '#7dd3fc',
}

const chartTooltipStyle = {
  background: '#2a292f',
  border: '1px solid rgba(144, 143, 160, 0.15)',
  borderRadius: '12px',
  color: '#e4e1e9',
  boxShadow: '0 20px 40px rgba(0, 0, 0, 0.3)',
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
      <div className="page-container text-center py-24">
        <p className="text-xl font-medium" style={{ color: '#c7c4d7' }}>No data available yet.</p>
        <p className="text-sm mt-2" style={{ color: '#64748b' }}>Analyze some reviews first to see statistics here.</p>
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
    <div className="page-container space-y-10 animate-fade-in">
      <h1 className="section-title text-3xl" style={{ letterSpacing: '-0.03em' }}>Dashboard</h1>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          icon={FiTrendingUp}
          label="Total Predictions"
          value={stats.totalPredictions.toLocaleString()}
          iconColor="#8083ff"
          iconBg="rgba(128, 131, 255, 0.1)"
        />
        <StatCard
          icon={FiThumbsUp}
          label="Positive"
          value={stats.positivePredictions.toLocaleString()}
          iconColor="#4edea3"
          iconBg="rgba(78, 222, 163, 0.1)"
        />
        <StatCard
          icon={FiThumbsDown}
          label="Negative"
          value={stats.negativePredictions.toLocaleString()}
          iconColor="#ffb4ab"
          iconBg="rgba(255, 180, 171, 0.1)"
        />
        <StatCard
          icon={FiTarget}
          label="Avg Confidence"
          value={`${(stats.averageConfidence * 100).toFixed(1)}%`}
          iconColor="#c4b5fd"
          iconBg="rgba(196, 181, 253, 0.1)"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Donut Chart */}
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-base font-semibold" style={{ color: '#e4e1e9' }}>Sentiment Distribution</h3>
          {stats.totalPredictions > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={donutData}
                  cx="50%"
                  cy="50%"
                  innerRadius={75}
                  outerRadius={115}
                  paddingAngle={3}
                  dataKey="value"
                  strokeWidth={0}
                >
                  <Cell fill={COLORS.positive} />
                  <Cell fill={COLORS.negative} />
                </Pie>
                <Tooltip contentStyle={chartTooltipStyle} />
                <Legend
                  wrapperStyle={{ color: '#908fa0', fontSize: '13px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-center py-20 text-sm" style={{ color: '#64748b' }}>No predictions yet</p>
          )}
        </div>

        {/* SMOTE Bar Chart */}
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-base font-semibold" style={{ color: '#e4e1e9' }}>SMOTE Class Distribution</h3>
          {smoteData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={smoteData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(144, 143, 160, 0.1)" />
                <XAxis dataKey="name" stroke="#908fa0" fontSize={12} tickLine={false} />
                <YAxis stroke="#908fa0" fontSize={12} tickLine={false} />
                <Tooltip contentStyle={chartTooltipStyle} />
                <Legend wrapperStyle={{ color: '#908fa0', fontSize: '13px' }} />
                <Bar dataKey="Negative" fill={COLORS.negative} radius={[6, 6, 0, 0]} />
                <Bar dataKey="Positive" fill={COLORS.positive} radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-center py-20 text-sm" style={{ color: '#64748b' }}>SMOTE data not available</p>
          )}
        </div>
      </div>

      {/* Charts Row 2 — Nouns & Adjectives */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Nouns */}
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-base font-semibold" style={{ color: '#e4e1e9' }}>Top Product Features</h3>
          {nounData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={nounData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(144, 143, 160, 0.1)" />
                <XAxis type="number" stroke="#908fa0" fontSize={12} tickLine={false} />
                <YAxis type="category" dataKey="name" width={80} stroke="#908fa0" fontSize={12} tickLine={false} />
                <Tooltip contentStyle={chartTooltipStyle} />
                <Bar dataKey="count" fill={COLORS.sky} radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-center py-20 text-sm" style={{ color: '#64748b' }}>No noun data yet</p>
          )}
        </div>

        {/* Top Adjectives */}
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-base font-semibold" style={{ color: '#e4e1e9' }}>Top Sentiment Descriptors</h3>
          {adjData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={adjData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(144, 143, 160, 0.1)" />
                <XAxis type="number" stroke="#908fa0" fontSize={12} tickLine={false} />
                <YAxis type="category" dataKey="name" width={80} stroke="#908fa0" fontSize={12} tickLine={false} />
                <Tooltip contentStyle={chartTooltipStyle} />
                <Bar dataKey="count" fill={COLORS.accent} radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-center py-20 text-sm" style={{ color: '#64748b' }}>No adjective data yet</p>
          )}
        </div>
      </div>

      {/* t-SNE Images */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-base font-semibold" style={{ color: '#e4e1e9' }}>t-SNE Before SMOTE</h3>
          <div className="rounded-xl overflow-hidden" style={{ background: '#0e0e13' }}>
            <img
              src={getTsneBefore()}
              alt="t-SNE visualization before SMOTE"
              className="w-full"
              onError={(e) => { e.target.style.display = 'none' }}
            />
          </div>
        </div>
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-base font-semibold" style={{ color: '#e4e1e9' }}>t-SNE After SMOTE</h3>
          <div className="rounded-xl overflow-hidden" style={{ background: '#0e0e13' }}>
            <img
              src={getTsneAfter()}
              alt="t-SNE visualization after SMOTE"
              className="w-full"
              onError={(e) => { e.target.style.display = 'none' }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ icon: Icon, label, value, iconColor, iconBg }) {
  return (
    <div className="stat-card group">
      <div className="w-10 h-10 rounded-xl flex items-center justify-center"
           style={{ background: iconBg }}>
        <Icon style={{ color: iconColor }} size={19} strokeWidth={2} />
      </div>
      <div className="mt-1">
        <p className="text-2xl font-bold tracking-tight" style={{ color: '#e4e1e9' }}>{value}</p>
        <p className="text-sm mt-0.5" style={{ color: '#908fa0' }}>{label}</p>
      </div>
    </div>
  )
}
