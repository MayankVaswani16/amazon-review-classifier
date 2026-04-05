export default function Spinner({ text = 'Loading...', size = 'md' }) {
  const dims = size === 'lg' ? 'w-10 h-10' : 'w-6 h-6'

  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16 animate-fade-in">
      <div className={`${dims} rounded-full border-2 border-transparent animate-spin`}
           style={{
             borderTopColor: '#8083ff',
             borderRightColor: 'rgba(128, 131, 255, 0.3)',
             borderBottomColor: 'transparent',
             borderLeftColor: 'transparent',
           }}
      />
      <p className="text-sm font-medium" style={{ color: '#908fa0' }}>{text}</p>
    </div>
  )
}
