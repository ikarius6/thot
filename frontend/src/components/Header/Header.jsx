import React from 'react';

const Header = ({ 
  search, 
  setSearch, 
  totalImages, 
  queueStatus, 
  onToggleQueue, 
  onStopQueue,
  onScanFolders,
  onOpenSettings,
  filter,
  setFilter
}) => {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-zinc-900/90 backdrop-blur-md border-b border-white/10 shadow-lg">
      <div className="max-w-[1920px] mx-auto px-6 h-20 flex items-center justify-between gap-6">
        
        {/* Logo */}
        <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
              Thot
            </h1>
        </div>

        {/* Search Bar */}
        <div className="flex-1 max-w-2xl relative group">
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
            <svg className="h-5 w-5 text-zinc-500 group-focus-within:text-blue-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <input
            type="text"
            className="block w-full pl-11 pr-4 py-2.5 bg-zinc-800/50 border border-white/10 rounded-xl 
                     text-zinc-200 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all font-medium"
            placeholder="Search tags..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {totalImages > 0 && (
            <div className="absolute inset-y-0 right-0 pr-4 flex items-center pointer-events-none">
              <span className="text-xs font-mono text-zinc-500">{totalImages} items</span>
            </div>
          )}
        </div>

        {/* Filters */}
        <div className="flex items-center bg-zinc-800/50 rounded-lg p-1 border border-white/5 mx-4 hidden md:flex">
          {[
            { key: 'all', label: 'All' },
            { key: 'untagged', label: 'Untagged' },
            { key: 'tagged', label: 'Tagged' },
          ].map(f => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                filter === f.key 
                  ? 'bg-zinc-700 text-white shadow-sm' 
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700/50'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button 
            onClick={onScanFolders}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-medium transition-colors border border-white/5"
          >
            <span>📁</span>
            <span className="hidden sm:inline">Folders</span>
          </button>

          <button 
            onClick={onOpenSettings}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-medium transition-colors border border-white/5"
            title="Settings"
          >
            <span>⚙️</span>
          </button>

          {/* Queue Status / Controls */}
          {queueStatus && (queueStatus.state === 'running' || queueStatus.state === 'paused') ? (
             <div className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800/80 rounded-lg border border-white/5">
                <span className="text-xs font-medium text-zinc-400">
                  {queueStatus.state === 'running' ? 'Running' : 'Paused'}
                </span>
                <button onClick={onToggleQueue} className="p-1 hover:bg-white/10 rounded" title={queueStatus.state === 'running' ? 'Pause' : 'Resume'}>
                  {queueStatus.state === 'running' ? '⏸️' : '▶️'}
                </button>
                <div className="w-px h-4 bg-white/10 mx-1" />
                <button onClick={onStopQueue} className="p-1 hover:bg-red-500/20 text-red-400 rounded" title="Stop">
                  ⏹️
                </button>
             </div>
          ) : (
             <button 
               className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium transition-all shadow-lg shadow-blue-500/20"
               onClick={onToggleQueue}
             >
               <span>🏷️</span>
               <span className="hidden sm:inline">
                 {queueStatus.untaggedCount > 0 ? `Auto Tag (${queueStatus.untaggedCount})` : 'Auto Tag'}
               </span>
             </button>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
