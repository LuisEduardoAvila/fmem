/**
 * Formatter for fmem search results.
 * Creates natural, conversational context for LLM injection.
 * Ported from Python fmem_integration.py
 */

import path from 'node:path';
import type { FmemSearchResult } from './fmem-client.js';

/**
 * Format search results for LLM context injection.
 * 
 * @param results - Search results from fmem
 * @param maxPreview - Maximum preview length per result (default 150)
 * @returns Formatted string ready for LLM context
 */
export function formatResults(
  results: FmemSearchResult[],
  maxPreview: number = 150
): string {
  if (!results || results.length === 0) {
    return '';
  }
  
  // Sort by score (highest first)
  const sortedResults = [...results].sort((a, b) => b.score - a.score);
  
  // Adaptive preview based on result count
  const resultCount = sortedResults.length;
  let previewLen: number;
  if (resultCount === 1) {
    previewLen = Math.min(maxPreview, 400);
  } else if (resultCount <= 3) {
    previewLen = Math.min(maxPreview, 250);
  } else {
    previewLen = Math.min(maxPreview, 150);
  }
  
  // Build output
  const output: string[] = [];
  output.push('<retrieved_memory>');
  output.push('');
  
  // Summary header
  if (resultCount === 1) {
    output.push('I found 1 relevant memory for this conversation:');
  } else {
    output.push(`I found ${resultCount} relevant memories for this conversation:`);
  }
  output.push('');
  
  // Group by source file
  const bySource = groupBySource(sortedResults);
  
  // Format each result with relevance ranking
  let idx = 0;
  for (const [filepath, fileResults] of bySource) {
    idx++;
    const filename = path.basename(filepath);
    const dirname = path.basename(path.dirname(filepath));
    
    // Determine relevance label
    const relevance = idx === 1 ? 'Most relevant' : idx === 2 ? 'Also relevant' : 'Related';
    
    // Document type context
    const docType = getDocType(filename, dirname);
    const sourceContext = `${docType} from ${dirname}/${filename}`;
    
    output.push(`[${idx}] ${relevance}: ${sourceContext}`);
    output.push(`   Source: ${filepath}`);
    output.push('');
    
    // Include each chunk from this file
    for (const r of fileResults) {
      const content = r.content;
      const preview = content.length > previewLen 
        ? content.substring(0, previewLen) + '...'
        : content;
      
      // Get heading if available
      const heading = r.heading;
      
      if (heading && heading !== 'Text') {
        output.push(`   Under '${heading}':`);
      }
      
      // Clean content for readability
      const cleanContent = cleanForLLm(preview);
      output.push(`   ${cleanContent}`);
      output.push('');
      
      // Show score if meaningful
      if (r.score > 0.5) {
        output.push(`   [relevance: ${Math.round(r.score * 100)}%]`);
        output.push('');
      }
    }
  }
  
  // Footer
  if (resultCount > 4) {
    output.push(`...and ${resultCount - 4} more related memories`);
    output.push('');
  }
  
  output.push('</retrieved_memory>');
  
  return output.join('\n');
}

/**
 * Group results by source file.
 */
function groupBySource(results: FmemSearchResult[]): Map<string, FmemSearchResult[]> {
  const bySource = new Map<string, FmemSearchResult[]>();
  
  for (const r of results) {
    const filepath = r.filepath;
    const existing = bySource.get(filepath) || [];
    existing.push(r);
    bySource.set(filepath, existing);
  }
  
  return bySource;
}

/**
 * Determine document type for context.
 */
function getDocType(filename: string, dirname: string): string {
  const lowername = filename.toLowerCase();
  const lowerdir = dirname.toLowerCase();
  
  if (lowerdir.includes('memory') || lowername.includes('memory')) {
    return 'Memory';
  }
  if (lowerdir.includes('docs') || lowerdir.includes('documentation')) {
    return 'Documentation';
  }
  if (lowerdir.includes('decisions') || lowername.includes('decisions')) {
    return 'Decision';
  }
  if (lowerdir.includes('projects')) {
    return 'Project notes';
  }
  if (lowerdir.includes('notes')) {
    return 'Notes';
  }
  if (lowername.endsWith('.md')) {
    return 'Document';
  }
  return 'File';
}

/**
 * Clean up text for better LLM readability.
 */
function cleanForLLm(text: string): string {
  // Remove leading/trailing whitespace
  let cleaned = text.trim();
  
  // Skip heading-only content
  if (/^#{1,6}\s/.test(cleaned) && cleaned.length < 50) {
    return '(Section heading)';
  }
  
  // Remove markdown heading markers
  cleaned = cleaned.replace(/^#{1,6}\s+/gm, '');
  
  // Remove markdown table separators
  cleaned = cleaned.replace(/\|[-:|\s]+\|/g, '');
  
  // Remove excessive newlines but preserve paragraph breaks
  const lines = cleaned.split('\n')
    .map(line => line.trim())
    .filter(line => line);
  cleaned = lines.join(' ');
  
  // Clean up multiple spaces
  cleaned = cleaned.replace(/\s+/g, ' ');
  
  return cleaned;
}