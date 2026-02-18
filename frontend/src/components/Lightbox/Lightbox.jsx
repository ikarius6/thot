import React, { useState, useEffect } from 'react';
import { api } from '../../api/api';

const Lightbox = ({ image, onClose, onUpdateImage }) => {
  const [details, setDetails] = useState(image);
  const [editingTags, setEditingTags] = useState(false);
  const [tagsList, setTagsList] = useState(image.tags ? image.tags.split(',').map(t => t.trim()).filter(Boolean) : []);
  const [newTag, setNewTag] = useState('');

  // Fetch full details (for duplicates, etc.) on open
  useEffect(() => {
    let active = true;
    api.get(`/images/${image.id}`).then(data => {
        if (active) {
            setDetails(data);
            const t = data.tags ? data.tags.split(',').map(t => t.trim()).filter(Boolean) : [];
            setTagsList(t);
        }
    }).catch(console.error);
    return () => { active = false; };
  }, [image.id]);

  // Handle ESC
  useEffect(() => {
    const handleKeyDown = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const handleAddTag = () => {
    const val = newTag.trim();
    if (val && !tagsList.includes(val)) {
        setTagsList([...tagsList, val]);
        setNewTag('');
    }
  };

  const handleRemoveTag = (index) => {
    const newTags = [...tagsList];
    newTags.splice(index, 1);
    setTagsList(newTags);
  };

  const handleSaveTags = async () => {
    try {
        const finalTags = tagsList.join(',');
        await api.put(`/images/${image.id}/tags?tags=${encodeURIComponent(finalTags)}`);
        const updated = { ...details, tags: finalTags };
        setDetails(updated);
        onUpdateImage(updated);
        setEditingTags(false);
    } catch (e) {
        console.error("Failed to save tags", e);
    }
  };

  const [isTagging, setIsTagging] = useState(false);

  const handleAIAutoTag = async () => {
    setIsTagging(true);
    try {
        await api.post(`/tag/${image.id}`);
        
        // Poll for updates
        let attempts = 0;
        const maxAttempts = 10;
        const interval = setInterval(async () => {
            attempts++;
            try {
                const data = await api.get(`/images/${image.id}`);
                if (data.tags) {
                    clearInterval(interval);
                    setDetails(data);
                    const t = data.tags ? data.tags.split(',').map(t => t.trim()).filter(Boolean) : [];
                    setTagsList(t);
                    onUpdateImage(data);
                    setIsTagging(false);
                }
            } catch (e) {
                console.error(e);
            }

            if (attempts >= maxAttempts) {
                clearInterval(interval);
                setIsTagging(false);
            }
        }, 4000);

        // Fallback cleanup
        setTimeout(() => {
            clearInterval(interval);
            setIsTagging(false);
        }, 45000);

    } catch (e) {
        console.error("AI Tagging failed", e);
        setIsTagging(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-xl flex items-center justify-center p-4 animate-in fade-in duration-200">
        <div className="absolute inset-0" onClick={onClose} />
        
        <div className="relative z-10 w-full max-w-7xl max-h-screen flex flex-col md:flex-row bg-zinc-900 border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
            {/* Image Container */}
            <div className="flex-1 bg-black flex items-center justify-center min-h-[40vh] md:min-h-[80vh] relative group">
                <img 
                    src={`${api.url('/images/')}${image.id}/full`} 
                    alt={details.filename}
                    className="max-h-full max-w-full object-contain"
                />
                <button 
                    onClick={onClose}
                    className="absolute top-4 right-4 bg-black/50 hover:bg-black/80 text-white rounded-full p-2 transition-colors"
                >
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>

            {/* Sidebar / Info */}
            <div className="w-full md:w-96 bg-zinc-900 border-l border-white/5 p-6 flex flex-col gap-6 overflow-y-auto max-h-[40vh] md:max-h-full">
                <div>
                    <h2 className="text-lg font-semibold text-zinc-100 break-all">{details.filename}</h2>
                    <p className="text-xs font-mono text-zinc-500 mt-1 break-all cursor-pointer hover:text-blue-400" onClick={() => navigator.clipboard.writeText(details.path)}>
                        {details.path}
                    </p>
                </div>

                {/* Tags Section */}
                <div className="flex-1">
                    <div className="flex items-center justify-between mb-2">
                        <h3 className="text-sm font-medium text-zinc-400">Tags</h3>
                        {!editingTags && (
                            <button 
                                onClick={() => {
                                    setTagsList(details.tags ? details.tags.split(',').map(t => t.trim()).filter(Boolean) : []);
                                    setEditingTags(true);
                                }} 
                                className="text-xs text-blue-400 hover:text-blue-300"
                            >
                                Edit
                            </button>
                        )}
                    </div>
                    
                    {editingTags ? (
                        <div className="flex flex-col gap-3">
                            <div className="flex flex-wrap gap-2 bg-zinc-800 border border-zinc-700 rounded p-2 min-h-[100px] max-h-[300px] overflow-y-auto">
                                {tagsList.map((tag, idx) => (
                                    <span key={idx} className="flex items-center gap-1 px-2 py-1 bg-blue-500/20 text-blue-300 border border-blue-500/30 rounded text-xs group">
                                        {tag}
                                        <button onClick={() => handleRemoveTag(idx)} className="hover:text-white ml-1">×</button>
                                    </span>
                                ))}
                                <input 
                                    className="flex-1 min-w-[120px] bg-transparent outline-none text-sm text-zinc-200 placeholder-zinc-600"
                                    placeholder="Add tag..."
                                    value={newTag}
                                    onChange={(e) => setNewTag(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' || e.key === ',') {
                                            e.preventDefault();
                                            handleAddTag();
                                        } else if (e.key === 'Backspace' && !newTag && tagsList.length > 0) {
                                            handleRemoveTag(tagsList.length - 1);
                                        }
                                    }}
                                />
                            </div>
                            <div className="flex gap-2">
                                <button onClick={handleSaveTags} className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white text-xs py-2 rounded">Save Changes</button>
                                <button onClick={() => setTagsList([])} className="px-3 bg-red-600/20 hover:bg-red-600/40 text-red-400 text-xs py-2 rounded border border-red-500/20" title="Delete All Tags">🗑️</button>
                                <button 
                                    onClick={() => {
                                        setEditingTags(false);
                                        setTagsList(details.tags ? details.tags.split(',').map(t => t.trim()).filter(Boolean) : []);
                                    }} 
                                    className="flex-1 bg-zinc-700 hover:bg-zinc-600 text-white text-xs py-2 rounded"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="flex flex-wrap gap-2">
                            {details.tags ? details.tags.split(',').map(tag => (
                                <span key={tag} className="px-2 py-1 bg-blue-500/10 text-blue-300 border border-blue-500/20 rounded-md text-xs">
                                    {tag.trim()}
                                </span>
                            )) : (
                                <span className="text-zinc-600 text-xs italic">No tags</span>
                            )}
                        </div>
                    )}
                </div>

                {/* Duplicates */}
                {details.duplicate_paths && details.duplicate_paths.length > 0 && (
                    <div className="bg-red-500/5 border border-red-500/10 rounded-lg p-3">
                        <h3 className="text-xs font-bold text-red-400 mb-2">Duplicates found ({details.duplicate_count})</h3>
                        <ul className="text-[10px] text-zinc-400 space-y-1 overflow-x-hidden">
                            {details.duplicate_paths.map((p, idx) => (
                                <li key={idx} className="break-all">• {p}</li>
                            ))}
                        </ul>
                    </div>
                )}
                
                {/* Actions */}
                <div className="mt-auto pt-4 border-t border-white/5">
                     <button 
                        onClick={handleAIAutoTag}
                        disabled={isTagging}
                        className="w-full py-3 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-xl shadow-lg shadow-blue-500/20 transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isTagging ? (
                            <span className="flex items-center justify-center gap-2">
                                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                Tagging...
                            </span>
                        ) : (
                            <span>✨ Auto Tag with AI</span>
                        )}
                    </button>
                </div>
            </div>
        </div>
    </div>
  );
};

export default Lightbox;
