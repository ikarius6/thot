import React from 'react';

const QueueProgress = ({ status }) => {
  if (!status || (status.state === 'idle' && status.total === 0)) return null;

  const percent = status.total > 0 ? (status.done / status.total) * 100 : 0;
  const isPaused = status.state === 'paused';

  return (
    <div className="mb-6 bg-zinc-800/40 border border-white/5 rounded-xl p-4 backdrop-blur-sm">
      <div className="flex justify-between items-center mb-2 text-sm">
        <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${isPaused ? 'bg-amber-500' : 'bg-emerald-500 animate-pulse'}`}></span>
            <span className="font-medium text-zinc-300">
                {isPaused ? 'Queue Paused' : (status.state === 'idle' && status.untaggedCount === 0) ? 'Finished' : (status.state === 'idle' && status.untaggedCount > 0) ? `Ready to Start (${status.untaggedCount} new)` : 'Tagging in progress...'}
            </span>
        </div>
        <div className="font-mono text-zinc-400">
            {status.done} / {status.total} <span className="text-zinc-600">({Math.round(percent)}%)</span>
        </div>
      </div>
      
      <div className="h-2 w-full bg-zinc-700/50 rounded-full overflow-hidden">
        <div 
            className={`h-full transition-all duration-500 ease-out ${isPaused ? 'bg-amber-500' : 'bg-blue-600'}`}
            style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
};

export default QueueProgress;
