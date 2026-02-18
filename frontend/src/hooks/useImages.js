import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/api';

const PAGE_SIZE = 50;

export function useImages() {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');

  const fetchImages = useCallback(async (pageNum = 1, append = false, activeFilter = filter, activeSearch = search) => {
    if (loading && append) return; 
    setLoading(true);
    try {
      let endpoint;
      if (activeSearch.length > 2) {
        endpoint = `/search?q=${encodeURIComponent(activeSearch)}&page=${pageNum}&page_size=${PAGE_SIZE}`;
      } else {
        const filterParam = activeFilter !== 'all' ? `&filter=${activeFilter}` : '';
        endpoint = `/images?page=${pageNum}&page_size=${PAGE_SIZE}${filterParam}`;
      }
      
      const data = await api.get(endpoint);
      
      if (append) {
        setImages(prev => {
          const existingIds = new Set(prev.map(img => img.id));
          const newImages = data.images.filter(img => !existingIds.has(img.id));
          return [...prev, ...newImages];
        });
      } else {
        setImages(data.images);
      }
      setTotal(data.total);
      setHasMore(pageNum * PAGE_SIZE < data.total);
    } catch (err) {
      console.error("Failed to fetch images", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const refresh = useCallback(() => {
    setPage(1);
    fetchImages(1, false, filter, search);
  }, [fetchImages, filter, search]);

  const loadMore = useCallback(() => {
    if (!loading && hasMore) {
      const nextPage = page + 1;
      setPage(nextPage);
      fetchImages(nextPage, true, filter, search);
    }
  }, [loading, hasMore, page, fetchImages, filter, search]);

  // Initial load
  useEffect(() => {
    refresh();
  }, [filter, search]); // Re-fetch when filter or search changes

  return {
    images,
    loading,
    hasMore,
    total,
    loadMore,
    refresh,
    setSearch: (val) => { setSearch(val); setPage(1); },
    setFilter: (val) => { setFilter(val); setPage(1); },
    search,
    filter,
    setImages // Expose setter for local updates (e.g. tagging)
  };
}
