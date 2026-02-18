import React, { useState, useEffect } from 'react';
import { api } from '../../api/api';

const FolderManager = ({ onClose, onScanComplete }) => {
  const [folders, setFolders] = useState([]);
  const [newPath, setNewPath] = useState('');
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    loadFolders();
  }, []);

  const loadFolders = async () => {
    setLoading(true);
    try {
        const data = await api.get('/folders');
        setFolders(data);
    } catch (e) {
        console.error(e);
    } finally {
        setLoading(false);
    }
  };

  const handleAdd = async () => {
    if (!newPath.trim()) return;
    setScanning(true);
    try {
        await api.post(`/scan?folder_path=${encodeURIComponent(newPath)}`);
        setNewPath('');
        await loadFolders();
        if (onScanComplete) onScanComplete();
    } catch (e) {
        console.error(e);
    } finally {
        setScanning(false);
    }
  };

  const handleRemove = async (id) => {
    try {
        await api.delete(`/folders/${id}`);
        setFolders(prev => prev.filter(f => f.id !== id));
    } catch (e) {
        console.error(e);
    }
  };

  const handleScanAll = async () => {
    setScanning(true);
    try {
        await api.post('/scan-all');
        if (onScanComplete) onScanComplete();
    } catch (e) {
        console.error(e);
    } finally {
        setScanning(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="absolute inset-0" onClick={onClose} />
      
      <div className="relative z-10 w-full max-w-2xl bg-zinc-900 border border-white/10 rounded-xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
        <div className="p-6 border-b border-white/5 flex justify-between items-center">
            <h2 className="text-xl font-bold text-white">Manage Folders</h2>
        </div>

        <div className="p-6">
            {/* List */}
            <div className="space-y-3 mb-6 max-h-60 overflow-y-auto">
                {loading ? (
                    <div className="text-zinc-500 text-center py-4">Loading...</div>
                ) : folders.length === 0 ? (
                    <div className="text-zinc-500 text-center py-8 border border-dashed border-zinc-700 rounded-lg">
                        No folders added yet.
                    </div>
                ) : (
                    folders.map(f => (
                        <div key={f.id} className="flex items-center justify-between bg-zinc-800/50 p-3 rounded-lg border border-white/5 group">
                            <span className="text-sm font-mono text-zinc-300 truncate mr-4">{f.path}</span>
                            <button 
                                onClick={() => handleRemove(f.id)}
                                className="text-zinc-500 hover:text-red-400 p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                                🗑️
                            </button>
                        </div>
                    ))
                )}
            </div>

            {/* Add New */}
            <div className="flex gap-2 mb-6">
                <button 
                    onClick={async () => {
                        try {
                            const data = await api.get('/system/pick-folder');
                            if (data.path) setNewPath(data.path);
                        } catch (e) {
                            console.error(e);
                            alert("Could not open folder picker (server-side feature).");
                        }
                    }}
                    className="bg-zinc-700 hover:bg-zinc-600 text-white px-3 py-2 rounded-lg font-medium transition-colors"
                    title="Browse Details"
                >
                    📂
                </button>
                <input 
                    type="text" 
                    placeholder="Enter folder path..." 
                    className="flex-1 bg-zinc-800 border-zinc-700 rounded-lg px-4 py-2 text-sm text-white focus:ring-2 focus:ring-blue-500 outline-none"
                    value={newPath}
                    onChange={(e) => setNewPath(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
                />
                <button 
                    onClick={handleAdd}
                    disabled={scanning || !newPath.trim()}
                    className="flex items-center gap-2 bg-zinc-700 hover:bg-zinc-600 text-white px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {scanning ? (
                        <>
                            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            <span>Scanning...</span>
                        </>
                    ) : (
                        <span>Add & Scan</span>
                    )}
                </button>
            </div>

            {/* Actions */}
            <div className="pt-6 border-t border-white/5 flex justify-end gap-3">
                <button onClick={onClose} className="px-4 py-2 text-zinc-400 hover:text-white transition-colors">Close</button>
                <button 
                    onClick={handleScanAll}
                    disabled={scanning || folders.length === 0}
                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-lg font-bold shadow-lg shadow-blue-500/20 transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {scanning ? (
                        <>
                            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            <span>Scanning All...</span>
                        </>
                    ) : (
                        <span>Scan All Folders</span>
                    )}
                </button>
            </div>
        </div>
      </div>
    </div>
  );
};

export default FolderManager;
