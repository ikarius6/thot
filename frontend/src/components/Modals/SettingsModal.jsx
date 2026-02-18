import React, { useState, useEffect } from 'react';
import { api } from '../../api/api';

const SettingsModal = ({ onClose }) => {
  const [settings, setSettings] = useState({ llm_model: '' });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
        const data = await api.get('/settings');
        // Default if not present
        if (!data.llm_model) {
            data.llm_model = "huihui_ai/qwen3-vl-abliterated:8b";
        }
        setSettings(data);
    } catch (e) {
        console.error(e);
    } finally {
        setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
        await api.post('/settings', settings);
        onClose();
    } catch (e) {
        console.error(e);
    } finally {
        setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="absolute inset-0" onClick={onClose} />
      
      <div className="relative z-10 w-full max-w-md bg-zinc-900 border border-white/10 rounded-xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
        <div className="p-6 border-b border-white/5 flex justify-between items-center">
            <h2 className="text-xl font-bold text-white">Settings</h2>
            <button onClick={onClose} className="text-zinc-500 hover:text-white">✕</button>
        </div>

        <div className="p-6 space-y-4">
            {loading ? (
                <div className="text-zinc-500 text-center py-4">Loading...</div>
            ) : (
                <div>
                    <label className="block text-sm font-medium text-zinc-400 mb-2">AI Model (Ollama)</label>
                    <input 
                        type="text" 
                        className="w-full bg-zinc-800 border-zinc-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-blue-500 outline-none"
                        value={settings.llm_model}
                        onChange={(e) => setSettings({...settings, llm_model: e.target.value})}
                    />
                    
                    {settings.llm_model && (
                        <div className="mt-3 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                            <h4 className="text-sm font-medium text-blue-400 mb-1">💡 Tips</h4>
                            <p className="text-xs text-zinc-400 mb-2">
                                1. Ensure <strong>Ollama</strong> is running in the background.
                            </p>
                            <p className="text-xs text-zinc-400">
                                2. If you haven't downloaded this model yet, run:
                            </p>
                            <div className="mt-1 flex items-center gap-2 bg-black/30 p-2 rounded border border-white/5 group relative">
                                <code className="text-xs font-mono text-zinc-300 flex-1">
                                    ollama pull {settings.llm_model}
                                </code>
                                <button 
                                    onClick={() => navigator.clipboard.writeText(`ollama pull ${settings.llm_model}`)}
                                    className="p-1 hover:bg-white/10 rounded text-zinc-500 hover:text-white transition-colors"
                                    title="Copy to clipboard"
                                >
                                    📋
                                </button>
                            </div>
                        </div>
                    )}

                    <p className="text-xs text-zinc-500 mt-2">
                        Common models: <code className="bg-zinc-800 px-1 rounded">huihui_ai/qwen3-vl-abliterated:8b</code>, <code className="bg-zinc-800 px-1 rounded">moondream</code>, <code className="bg-zinc-800 px-1 rounded">llava</code>
                    </p>
                </div>
            )}
        </div>

        <div className="p-6 border-t border-white/5 flex justify-end gap-3">
            <button onClick={onClose} className="px-4 py-2 text-zinc-400 hover:text-white transition-colors">Cancel</button>
            <button 
                onClick={handleSave}
                disabled={saving || loading}
                className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-lg font-bold shadow-lg shadow-blue-500/20 transition-all active:scale-95 disabled:opacity-50"
            >
                {saving ? 'Saving...' : 'Save Settings'}
            </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
