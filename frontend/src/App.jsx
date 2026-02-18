import React, { useState } from 'react';
import { useImages } from './hooks/useImages';
import { useQueue } from './hooks/useQueue';
import Layout from './components/Layout/Layout';
import Header from './components/Header/Header';
import Gallery from './components/Gallery/Gallery';
import Lightbox from './components/Lightbox/Lightbox';
import QueueProgress from './components/Queue/QueueProgress';
import FolderManager from './components/Modals/FolderManager';
import SettingsModal from './components/Modals/SettingsModal';

function App() {
  const { 
    images, loading, hasMore, loadMore, 
    search, setSearch, total, refresh, setImages,
    filter, setFilter
  } = useImages();
  
  const queue = useQueue();
  
  const [lightboxImage, setLightboxImage] = useState(null);
  const [showFolderManager, setShowFolderManager] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [taggingIds, setTaggingIds] = useState(new Set());

  // Handle queue toggle
  const toggleQueue = () => {
    if (queue.status.state === 'running') {
      queue.pause();
    } else if (queue.status.state === 'paused') {
      queue.resume();
    } else {
      queue.start();
    }
  };

  const handleScanFolders = () => {
    setShowFolderManager(true);
  };

  const handleOpenSettings = () => {
    setShowSettingsModal(true);
  };

  const handleCloseFolderManager = () => {
    setShowFolderManager(false);
    refresh(); 
  };
  
  const handleUpdateImage = (updatedImg) => {
    setImages(prev => prev.map(img => img.id === updatedImg.id ? updatedImg : img));
    if (lightboxImage?.id === updatedImg.id) {
        setLightboxImage(updatedImg);
    }
  };

  return (
    <Layout
      header={
        <Header 
          search={search}
          setSearch={setSearch}
          totalImages={total}
          queueStatus={queue.status}
          onToggleQueue={toggleQueue}
          onStopQueue={queue.stop}
          onScanFolders={handleScanFolders}
          onOpenSettings={handleOpenSettings}
          filter={filter}
          setFilter={setFilter}
        />
      }
    >
      <QueueProgress status={queue.status} />
      
      <Gallery 
        images={images}
        loading={loading}
        hasMore={hasMore}
        loadMore={loadMore}
        onImageClick={setLightboxImage}
        taggingIds={taggingIds}
      />

      {lightboxImage && (
        <Lightbox 
          image={lightboxImage} 
          onClose={() => setLightboxImage(null)} 
          onUpdateImage={handleUpdateImage}
        />
      )}

      {showFolderManager && (
        <FolderManager 
          onClose={handleCloseFolderManager} 
          onScanComplete={refresh}
        />
      )}

      {showSettingsModal && (
        <SettingsModal 
          onClose={() => setShowSettingsModal(false)}
        />
      )}

    </Layout>
  );
}

export default App;
