/**
 * CLI wrapper for fmem search.
 * Calls the Python fmem CLI for memory retrieval.
 */

// Try importing runExec from plugin SDK - this may not be available to workspace plugins
// @ts-expect-error - runExec may not be exported to plugins
import { runExec } from '@openclaw/plugin-sdk/process-runtime';
import type { PluginConfig } from './types.js';

/** CLI command to invoke */
const FMEM_CLI = 'fmem';

/**
 * Search result from fmem CLI.
 */
export interface FmemSearchResult {
  filepath: string;
  content: string;
  score: number;
  heading?: string;
}

/**
 * Check if fmem CLI is available and working.
 */
export async function isFmemAvailable(): Promise<boolean> {
  try {
    // fmem doesn't support --version, use status command instead
    // Status output goes to both stdout and stderr
    console.log('[fmem-auto] checking fmem availability...');
    const result = await runExec(FMEM_CLI, ['status'], { timeoutMs: 5000 });
    console.log('[fmem-auto] fmem status stdout:', result.stdout?.slice(0, 100));
    console.log('[fmem-auto] fmem status stderr:', result.stderr?.slice(0, 100));
    const output = result.stdout + result.stderr;
    const available = output.includes('Documents indexed') || output.includes('Total chunks') || output.includes('fmem');
    console.log('[fmem-auto] fmem available result:', available);
    return available;
  } catch (error) {
    console.log('[fmem-auto] fmem check error:', error);
    return false;
  }
}

/**
 * Call fmem CLI to search for memories.
 * 
 * @param query - Search query
 * @param topK - Number of results to return (default from config or 3)
 * @param minScore - Minimum relevance score (default from config or 0.25)
 * @param config - Plugin config with timeout settings
 * @returns Parsed search results
 */
export async function fmemSearch(
  query: string,
  topK: number = 3,
  minScore: number = 0.25,
  config?: PluginConfig
): Promise<FmemSearchResult[]> {
  const timeoutMs = config?.timeoutMs ?? 5000;
  
  try {
    // Build args array (avoids shell injection)
    const args = [
      'search',
      '--json',
      '-k', topK.toString(),
      '--min-score', minScore.toString(),
      query
    ];
    
    const result = await runExec(FMEM_CLI, args, { timeoutMs });
    
    if (!result.stdout.trim()) {
      return [];
    }
    
    // Parse JSON output
    const parsed = JSON.parse(result.stdout);
    
    // Handle both array and object responses
    if (Array.isArray(parsed)) {
      return filterAndFormatResults(parsed, minScore);
    }
    
    if (parsed.results && Array.isArray(parsed.results)) {
      return filterAndFormatResults(parsed.results, minScore);
    }
    
    return [];
    
  } catch (error) {
    // Graceful degradation - log and return empty
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.warn(`fmem search failed: ${errorMsg}`);
    return [];
  }
}

/**
 * Filter results by minimum relevance score and format.
 */
function filterAndFormatResults(
  results: Array<Record<string, unknown>>,
  minScore: number
): FmemSearchResult[] {
  return results
    .filter(r => (r.score as number) >= minScore)
    .map(r => ({
      filepath: (r.filepath as string) || '',
      content: (r.content as string) || '',
      score: (r.score as number) || 0,
      heading: (r.chunk_info as Record<string, unknown>)?.heading as string | undefined,
    }));
}