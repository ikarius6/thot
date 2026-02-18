import React, { useRef, useEffect } from 'react';
import ImageCard from './ImageCard';

const Gallery = ({ images, loading, hasMore, loadMore, onImageClick, taggingIds }) => {
  const sentinelRef = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && !loading && hasMore) {
        loadMore();
      }
    }, { rootMargin: '400px' });

    if (sentinelRef.current) observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [loading, hasMore, loadMore]);

  if (images.length === 0 && !loading) {
    return (
        <div className="flex flex-col items-center justify-center py-20 opacity-50">
            <div className="text-6xl mb-4">🖼️</div>
            <h2 className="text-xl font-semibold">No images found</h2>
            <p className="text-sm">Try adjusting your search or scan a folder.</p>
        </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-2 xs:grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-8 2xl:grid-cols-10 gap-0">
        {images.map((img) => (
          <ImageCard
            key={img.id}
            image={img}
            onClick={onImageClick}
            isTagging={taggingIds && taggingIds.has(img.id)}
          />
        ))}
      </div>
      
      {/* Sentinel / Loading State */}
      <div ref={sentinelRef} className="py-8 flex justify-center">
        {loading && (
            <div className="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
        )}
        {!hasMore && images.length > 0 && (
            <div className="text-zinc-600 text-sm italic">End of results</div>
        )}
      </div>
    </>
  );
};

export default Gallery;
