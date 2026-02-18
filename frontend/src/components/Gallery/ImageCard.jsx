import React from 'react';
import { api } from '../../api/api';

// Helper to determine if image is tagged
const isTagged = (img) => img.tags && img.tags.length > 0;

const ImageCard = ({ image, onClick, onTag, isTagging }) => {
  const thumbnailSrc = `${api.url('/thumbnails/')}${image.id}.jpg`;
  
  return (
    <div 
      className="relative group cursor-pointer overflow-hidden bg-zinc-800 aspect-square"
      onClick={() => onClick(image)}
    >
      <img
        src={thumbnailSrc}
        alt={image.filename}
        loading="lazy"
        className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
        onError={(e) => {
            e.target.onerror = null; 
            e.target.src = "https://via.placeholder.com/200?text=Error"
        }}
      />
      
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-2">
         {/* Top badges */}
         <div className="absolute top-2 right-2 flex gap-1">
            {image.duplicate_count > 1 && (
                <span className="bg-red-500/90 text-white text-[10px] font-bold px-1.5 py-0.5 rounded shadow">
                    {image.duplicate_count}x
                </span>
            )}
            {isTagging && (
                <span className="bg-blue-500/90 text-white text-[10px] font-bold px-1.5 py-0.5 rounded shadow animate-pulse">
                    ...
                </span>
            )}
         </div>

         {/* Bottom Info */}
         <div className="transform translate-y-4 group-hover:translate-y-0 transition-transform duration-300">
            <p className="text-white text-xs font-medium truncate drop-shadow-md">
                {image.filename}
            </p>
            <div className="flex items-center justify-between mt-1">
                <span className={`w-2 h-2 rounded-full ${isTagged(image) ? 'bg-emerald-400' : 'bg-zinc-500'}`} />
                <button 
                    onClick={(e) => {
                        e.stopPropagation();
                        // copy path
                        navigator.clipboard.writeText(image.path);
                    }}
                    className="text-zinc-300 hover:text-white text-[10px] bg-black/50 px-1.5 py-0.5 rounded"
                >
                    Copy
                </button>
            </div>
         </div>
      </div>
    </div>
  );
};

export default ImageCard;
