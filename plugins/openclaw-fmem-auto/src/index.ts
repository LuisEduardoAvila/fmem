/**
 * OpenClaw fmem Auto-Recall Plugin
 * 
 * Automatic memory recall plugin that injects relevant memories
 * into prompts based on conversational triggers.
 * 
 * P0/P1 Fixes Applied:
 * - P0-1: Use runExec from @openclaw/plugin-sdk/process-runtime
 * - P0-2: Use register() pattern instead of hooks property
 * - P0-3: Define types locally in types.ts
 * - P0-6: Session-scoped cache (not global)
 * - P0-7: Rate limiting per session
 * - P1-1: Consume config values
 * - P1-2: Check enabled config
 * - P1-5: Cache cleanup on each search
 * - P1-8: Null/undefined message validation
 */

import { definePluginEntry } from './sdk-stub.js';
import type {
  PluginHookBeforePromptBuildEvent,
  PluginHookBeforePromptBuildResult,
  PluginHookAgentContext,
  PluginConfig,
} from './types.js';
import { shouldSearch, extractSearchQuery } from './triggers.js';
import { fmemSearch, isFmemAvailable } from './fmem-client.js';
import { formatResults } from './formatter.js';

/** Deduplication TTL (5 minutes) */
const DEDUPE_TTL_MS = 5 * 60 * 1000;

/** Rate limiting: minimum time between searches per session */
const MIN_SEARCH_INTERVAL_MS = 1000; // 1 second

/** Maximum message length to process (DoS protection) */
const MAX_MESSAGE_LENGTH = 10000;

/** Session-scoped caches (P0-6: not global) */
const sessionCaches = new Map<string, Map<string, number>>();
const sessionLastSearch = new Map<string, number>();

/**
 * Get or create a session-specific cache.
 */
function getSessionCache(sessionId: string): Map<string, number> {
  if (!sessionCaches.has(sessionId)) {
    sessionCaches.set(sessionId, new Map());
  }
  return sessionCaches.get(sessionId)!;
}

/**
 * Check if a file was recently recalled (for deduplication).
 */
function wasRecentlyRecalled(cache: Map<string, number>, filepath: string): boolean {
  const lastRecalled = cache.get(filepath);
  if (!lastRecalled) return false;
  return Date.now() - lastRecalled < DEDUPE_TTL_MS;
}

/**
 * Mark a file as recalled.
 */
function markRecalled(cache: Map<string, number>, filepath: string): void {
  cache.set(filepath, Date.now());
}

/**
 * Clean expired entries from cache (P1-5).
 */
function cleanupCache(cache: Map<string, number>): void {
  const now = Date.now();
  for (const [key, timestamp] of cache.entries()) {
    if (now - timestamp > DEDUPE_TTL_MS) {
      cache.delete(key);
    }
  }
}

/**
 * Find the last user message from the messages array.
 * Handles string content and array content (multi-modal).
 * P1-8: Added null/undefined validation.
 * Skips system-injected context (messages starting with "System:").
 */
function getLastUserMessage(messages: unknown[]): string | null {
  if (!Array.isArray(messages)) return null;
  
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    
    // P1-8: Defensive check for null/undefined
    if (!msg || typeof msg !== 'object') continue;
    
    const msgObj = msg as Record<string, unknown>;
    if (msgObj.role !== 'user') continue;
    
    const content = msgObj.content;
    
    // Get text content
    let textContent = '';
    if (typeof content === 'string' && content.trim()) {
      textContent = content;
    } else if (Array.isArray(content)) {
      textContent = content
        .filter(part => part && typeof part === 'object' && (part as Record<string, unknown>).type === 'text')
        .map(part => (part as Record<string, unknown>).text as string)
        .join(' ');
    }
    
    if (!textContent.trim()) continue;
    
    // Skip system-injected content (starts with "System:")
    if (textContent.startsWith('System:')) {
      continue;
    }
    
    return textContent;
  }
  return null;
}

/**
 * before_prompt_build hook handler.
 * Analyzes user messages and injects relevant memories.
 */
async function beforePromptBuild(
  event: PluginHookBeforePromptBuildEvent,
  ctx: PluginHookAgentContext
): Promise<PluginHookBeforePromptBuildResult | void> {
  // Debug: Log that hook was called
  console.log('[fmem-auto] before_prompt_build hook called');
  
  try {
    // P1-2: Check if plugin is enabled
    const config = ctx.config as PluginConfig | undefined;
    if (config?.enabled === false) {
      console.log('[fmem-auto] Plugin disabled, skipping');
      return;
    }
    
    // Get session ID for cache scoping (P0-6)
    const sessionId = event.sessionId || 'default';
    console.log('[fmem-auto] sessionId:', sessionId);
    
    // P0-7: Rate limiting per session
    const lastSearch = sessionLastSearch.get(sessionId) || 0;
    if (Date.now() - lastSearch < MIN_SEARCH_INTERVAL_MS) {
      console.log('[fmem-auto] Rate limited, skipping');
      return; // Skip, too soon
    }
    
    // Get the last user message
    const messages = event.messages as unknown[];
    const lastUserMessage = getLastUserMessage(messages);
    console.log('[fmem-auto] lastUserMessage:', lastUserMessage?.slice(0, 100));
    
    if (!lastUserMessage) {
      console.log('[fmem-auto] No user message found');
      return;
    }
    
    // P1-6: Input size validation
    if (lastUserMessage.length > MAX_MESSAGE_LENGTH) {
      return;
    }
    
    // Check if search should be triggered (P1-1: pass config)
    const shouldSearchResult = shouldSearch(lastUserMessage, config);
    console.log('[fmem-auto] shouldSearch:', shouldSearchResult);
    if (!shouldSearchResult) {
      return;
    }
    
    // Check if fmem is available
    const available = await isFmemAvailable();
    console.log('[fmem-auto] fmem available:', available);
    if (!available) {
      ctx.logger?.warn?.('fmem CLI not available, skipping memory recall');
      return;
    }
    
    // Mark this session as having searched (P0-7)
    sessionLastSearch.set(sessionId, Date.now());
    
    // Get session-scoped cache (P0-6)
    const cache = getSessionCache(sessionId);
    
    // P1-5: Clean expired entries
    cleanupCache(cache);
    
    // Extract search query
    const query = extractSearchQuery(lastUserMessage);
    console.log('[fmem-auto] search query:', query);
    
    // P1-1: Use config values
    const topK = config?.topK ?? 3;
    const minScore = config?.minScore ?? 0.25;
    
    // Perform search
    const results = await fmemSearch(query, topK, minScore, config);
    console.log('[fmem-auto] results:', results.length);
    
    if (results.length === 0) {
      return;
    }
    
    // Filter out recently recalled files (deduplication)
    const filteredResults = results.filter(r => !wasRecentlyRecalled(cache, r.filepath));
    
    if (filteredResults.length === 0) {
      return;
    }
    
    // Mark files as recalled
    for (const r of filteredResults) {
      markRecalled(cache, r.filepath);
    }
    
    // Format results for LLM context
    const prependContext = formatResults(filteredResults);
    
    return { prependContext };
    
  } catch (error) {
    // Graceful degradation - log and return empty result
    const errorMsg = error instanceof Error ? error.message : String(error);
    ctx.logger?.warn?.(`fmem auto-recall failed: ${errorMsg}`);
    return;
  }
}

// Plugin entry point using register() pattern (P0-2)
export default definePluginEntry({
  id: 'fmem-auto',
  name: 'fmem Auto-Recall',
  description: 'Automatically recall relevant memories based on conversation context',
  version: '1.0.0',
  register(api) {
    api.on('before_prompt_build', beforePromptBuild, { name: 'fmem-auto-before-prompt' });
  },
});