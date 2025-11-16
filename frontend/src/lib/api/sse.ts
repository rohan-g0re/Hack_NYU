import { API_BASE_URL } from '../constants';
import type { NegotiationEvent } from '../types';

/**
 * Opens a Server-Sent Events stream for a negotiation room
 * @param roomId The negotiation room ID
 * @param onEvent Callback function called for each event
 * @returns Cleanup function to close the stream
 */
export function openNegotiationStream(
  roomId: string,
  onEvent: (event: NegotiationEvent) => void
): () => void {
  const url = `${API_BASE_URL}/api/v1/negotiation/${roomId}/stream`;
  console.log('Opening SSE stream to:', url);
  
  const eventSource = new EventSource(url);

  eventSource.onopen = () => {
    console.log('SSE connection opened successfully');
  };

  eventSource.onmessage = (ev) => {
    console.log('SSE message received:', ev.data);
    try {
      const data = JSON.parse(ev.data) as NegotiationEvent;
      onEvent(data);
    } catch (error) {
      console.error('Failed to parse SSE event:', error, ev.data);
    }
  };

  eventSource.onerror = (error) => {
    console.error('SSE connection error:', error);
    console.error('EventSource readyState:', eventSource.readyState);
    console.error('EventSource URL:', eventSource.url);
    
    // readyState values:
    // 0 = CONNECTING
    // 1 = OPEN
    // 2 = CLOSED
    
    if (eventSource.readyState === EventSource.CLOSED) {
      console.error('SSE connection closed. The stream may have ended or encountered an error.');
    } else if (eventSource.readyState === EventSource.CONNECTING) {
      console.log('SSE attempting to reconnect...');
    }
  };

  // Return cleanup function
  return () => {
    console.log('Closing SSE connection');
    eventSource.close();
  };
}

