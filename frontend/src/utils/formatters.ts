import { format, formatDistanceToNow } from 'date-fns';

/**
 * Format a number as currency (USD)
 */
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

/**
 * Format a timestamp to a readable time string
 */
export function formatTimestamp(date: string | Date, formatStr: string = 'HH:mm:ss'): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return format(dateObj, formatStr);
}

/**
 * Format a full datetime
 */
export function formatDateTime(date: string | Date): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return format(dateObj, 'MMM dd, yyyy \'at\' h:mm a');
}

/**
 * Format relative time (e.g., "2 minutes ago")
 */
export function formatRelativeTime(date: string | Date): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return formatDistanceToNow(dateObj, { addSuffix: true });
}

/**
 * Format duration in seconds to human-readable string (e.g., "2m 25s")
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);

  if (remainingSeconds === 0) {
    return `${minutes}m`;
  }

  return `${minutes}m ${remainingSeconds}s`;
}

/**
 * Escape HTML special characters to prevent injection
 */
export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Remove reasoning/thinking segments like <think>...</think> and common prefixes
 */
export function stripThinking(text: string): string {
  if (!text) return '';
  
  // Remove DeepSeek-style <think>...</think> blocks
  let out = text.replace(/<think>[\s\S]*?<\/think>/gi, '');
  // Remove dangling <think> without closing tag
  out = out.replace(/<think>[\s\S]*$/gi, '');
  // Remove stray closing tags
  out = out.replace(/<\/think>/gi, '');
  
  // Remove common reasoning prefixes on their own lines
  out = out.replace(/^\s*(?:Thought|Thinking|Reasoning|Analysis|Chain of thought)\s*:\s*.*(\r?\n|$)/gmi, '');
  
  // Collapse extra whitespace and trim
  return out.replace(/\s+/g, ' ').trim();
}

/**
 * Highlight @mentions in text by wrapping them in span tags (safely escapes HTML first)
 */
export function highlightMentions(text: string): string {
  const safe = escapeHtml(text);
  return safe.replace(/@(\w+)/g, '<span class="mention">@$1</span>');
}

/**
 * Format a number with commas for thousands separators
 */
export function formatNumber(num: number): string {
  return new Intl.NumberFormat('en-US').format(num);
}

/**
 * Truncate text to a maximum length with ellipsis
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}

