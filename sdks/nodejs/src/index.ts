/**
 * Mandate Vault Node.js SDK
 * ==========================
 * 
 * Official Node.js/TypeScript client for Mandate Vault API.
 * 
 * Installation:
 *   npm install mandate-vault
 * 
 * Usage:
 *   import { MandateVaultClient } from 'mandate-vault';
 *   
 *   const client = new MandateVaultClient({ apiKey: 'mvk_your_key' });
 *   const mandate = await client.mandates.create({
 *     vcJwt: '...',
 *     tenantId: '...'
 *   });
 */

export { MandateVaultClient } from './client';
export * from './types';
export * from './errors';

export const VERSION = '1.0.0';

