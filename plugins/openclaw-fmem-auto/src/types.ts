/**
 * Type definitions for fmem-auto plugin.
 * These types are defined locally since the SDK does not export them.
 */

/**
 * Message content can be a string or an array of content parts.
 */
export type MessageContent = string | Array<{ type: string; text?: string }>;

/**
 * A message in the conversation.
 */
export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: MessageContent;
}

/**
 * Event passed to the before_prompt_build hook.
 */
export interface PluginHookBeforePromptBuildEvent {
  /** The user's message text (already extracted by OpenClaw) */
  prompt: string;
  /** The conversation history */
  messages: Message[];
  sessionId?: string;
}

/**
 * Result returned from the before_prompt_build hook.
 */
export interface PluginHookBeforePromptBuildResult {
  prependContext?: string;
}

/**
 * Context passed to hook handlers.
 */
export interface PluginHookAgentContext {
  config?: PluginConfig;
  logger?: {
    warn: (msg: string) => void;
    info: (msg: string) => void;
    debug?: (msg: string) => void;
  };
}

/**
 * Plugin configuration from openclaw.plugin.json.
 */
export interface PluginConfig {
  enabled?: boolean;
  topK?: number;
  minScore?: number;
  timeoutMs?: number;
  gracefulDegradation?: boolean;
  triggers?: {
    explicit?: string[];
    recency?: string[];
    location?: string[];
    context?: string[];
  };
}