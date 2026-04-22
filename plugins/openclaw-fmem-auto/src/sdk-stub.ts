/**
 * Type stubs for @openclaw/plugin-sdk
 * 
 * This file provides type definitions for the plugin SDK.
 * The actual SDK is not published to npm, so we use these stubs.
 */

// From plugin-entry.ts
export interface OpenClawPluginApi {
  on<T = unknown, C = unknown>(event: string, handler: (event: T, ctx: C) => Promise<unknown> | unknown, opts?: { name: string }): void;
  registerHook(hookName: string, handler: Function): void;
  registerCommand(command: { name: string; description: string; acceptsArgs?: boolean; handler: (ctx: unknown) => Promise<unknown> }): void;
  pluginConfig: Record<string, unknown>;
  runtime: {
    config: {
      loadConfig(): Record<string, unknown>;
      writeConfigFile(config: Record<string, unknown>): Promise<void>;
    };
  };
  logger: { warn: (msg: string) => void; info: (msg: string) => void; debug?: (msg: string) => void };
}

export interface DefinedPluginEntry {
  id: string;
  name: string;
  description: string;
  version?: string;
  kind?: string;
  configSchema?: unknown;
  reload?: (ctx: unknown) => Promise<void>;
  nodeHostCommands?: unknown[];
  securityAuditCollectors?: unknown[];
  register?: (api: OpenClawPluginApi) => void;
}

export interface DefinePluginEntryOptions {
  id: string;
  name: string;
  description: string;
  version?: string;
  kind?: string;
  configSchema?: unknown;
  reload?: (ctx: unknown) => Promise<void>;
  nodeHostCommands?: unknown[];
  securityAuditCollectors?: unknown[];
  register?: (api: OpenClawPluginApi) => void;
}

export function definePluginEntry(options: DefinePluginEntryOptions): DefinedPluginEntry {
  return {
    id: options.id,
    name: options.name,
    description: options.description,
    ...(options.version ? { version: options.version } : {}),
    ...(options.kind ? { kind: options.kind } : {}),
    configSchema: options.configSchema,
    reload: options.reload,
    nodeHostCommands: options.nodeHostCommands,
    securityAuditCollectors: options.securityAuditCollectors,
    register: options.register,
  };
}