import { useState, useEffect, useRef } from 'react';
import { api } from '../api/api';

export function useQueue() {
  const [status, setStatus] = useState({ state: 'idle', total: 0, done: 0, errors: 0, pending: 0, current_image_id: null });
  const intervalRef = useRef(null);

  const fetchStatus = async () => {
    try {
      const [queueData, untaggedData] = await Promise.all([
        api.get('/queue/status'),
        api.get('/images?filter=untagged&page_size=1')
      ]);
      
      setStatus({
        ...queueData,
        untaggedCount: untaggedData.total
      });
      return queueData;
    } catch (e) {
      console.error(e);
      return null;
    }
  };

  useEffect(() => {
    fetchStatus();
    intervalRef.current = setInterval(fetchStatus, 3000);
    return () => clearInterval(intervalRef.current);
  }, []);

  const start = async () => {
    await api.post('/queue/start');
    fetchStatus();
  };

  const pause = async () => {
    await api.post('/queue/pause');
    fetchStatus();
  };

  const resume = async () => {
    await api.post('/queue/resume');
    fetchStatus();
  };

  const stop = async () => {
    await api.post('/queue/stop');
    fetchStatus();
  };

  return {
    status,
    start,
    pause,
    resume,
    stop
  };
}
