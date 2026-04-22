/**
 * Search trigger patterns for automatic memory recall.
 * Ported from Python fmem_integration.py
 */

import type { PluginConfig } from './types.js';

/** Maximum message length to process (prevent DoS) */
const MAX_MESSAGE_LENGTH = 10000;

/** Default trigger patterns */
const DEFAULT_TRIGGERS = {
  explicit: [
    /\b(look up|find|search|recall|remember)\b/i,
    /\b(what (did|was|were)|when did)\b/i,
    /\b(show me|tell me about)\b/i,
  ],
  recency: [
    /\b(last|recent|previous|earlier)\s+(week|month|day|session|conversation)\b/i,
    /\b(yesterday|before|recently)\b/i,
  ],
  location: [
    /\b(in|under|from)\s+([\w-]+\/[\w-]+)/i,
    /\b(docs|projects|notes|memory|personas)\b/i,
  ],
  context: [
    /\b(my|our)\s+(preferences|settings|goals|projects)\b/i,
    /\b(Luis|workspace|setup)\b/i,
  ],
};

/**
 * Determine if a message should trigger memory search.
 * 
 * @param message - User message text
 * @param config - Optional plugin config with custom triggers
 * @returns True if search should be triggered
 */
export function shouldSearch(
  message: string,
  config?: PluginConfig
): boolean {
  // Input validation: reject overly long messages (DoS protection)
  if (message.length > MAX_MESSAGE_LENGTH) {
    return false;
  }

  const messageLower = message.toLowerCase();
  
  // Use custom triggers if provided, otherwise defaults
  const triggers = config?.triggers ?? DEFAULT_TRIGGERS;
  
  // Check explicit triggers (string patterns converted to regex)
  if (triggers.explicit) {
    for (const pattern of triggers.explicit) {
      const regex = typeof pattern === 'string' ? new RegExp(pattern, 'i') : pattern;
      if (regex.test(messageLower)) return true;
    }
  }
  
  // Check recency triggers
  if (triggers.recency) {
    for (const pattern of triggers.recency) {
      const regex = typeof pattern === 'string' ? new RegExp(pattern, 'i') : pattern;
      if (regex.test(messageLower)) return true;
    }
  }
  
  // Check location triggers
  if (triggers.location) {
    for (const pattern of triggers.location) {
      const regex = typeof pattern === 'string' ? new RegExp(pattern, 'i') : pattern;
      if (regex.test(messageLower)) return true;
    }
  }
  
  // Check context triggers
  if (triggers.context) {
    for (const pattern of triggers.context) {
      const regex = typeof pattern === 'string' ? new RegExp(pattern, 'i') : pattern;
      if (regex.test(messageLower)) return true;
    }
  }
  
  return false;
}

/** Trigger words to strip from search queries */
const TRIGGER_WORDS = [
  'look', 'looked', 'looking', 'lookup', 'looked',
  'find', 'found', 'finding', 'finds',
  'search', 'searched', 'searching', 'searches',
  'recall', 'recalled', 'recalling', 'recalls',
  'remember', 'remembered', 'remembering', 'remembers',
  'show', 'showed', 'showing', 'shows',
  'tell', 'told', 'telling', 'tells',
  'what', 'when', 'where', 'which', 'who', 'whom', 'whose',
  'did', 'does', 'would', 'could', 'should',
  'about', 'me', 'my', 'our', 'the', 'a', 'an',
];

/** Trigger word set for O(1) lookup */
const TRIGGER_WORD_SET = new Set(TRIGGER_WORDS.map(w => w.toLowerCase()));

/**
 * Extract relevant search terms from message.
 * Strips trigger words that dilute semantic matching.
 * 
 * @param message - User message text
 * @returns Extracted search query
 */
export function extractSearchQuery(message: string): string {
  // Remove common filler words
  const filler = /\b(please|can you|could you|would you|i want to|i need|i'd like)\b/gi;
  const cleaned = message.replace(filler, '');
  
  // Extract key content words (3+ chars)
  const words = cleaned.match(/\b[a-z]{3,}\b/gi) || [];
  
  // Filter out trigger words and take meaningful words (limit to 10)
  const filtered = words
    .filter(w => !TRIGGER_WORD_SET.has(w.toLowerCase()))
    .slice(0, 10);
  
  const query = filtered.join(' ');
  
  return query || message.slice(0, 100);
}