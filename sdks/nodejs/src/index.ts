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
 *   
 *   // Multi-protocol authorizations (NEW - recommended)
 *   const auth = await client.authorizations.create({
 *     protocol: 'ACP',
 *     payload: {
 *       tokenId: 'acp-123',
 *       pspId: 'psp-stripe',
 *       merchantId: 'merchant-456',
 *       maxAmount: '5000.00',
 *       currency: 'USD',
 *       expiresAt: '2026-01-01T00:00:00Z',
 *       constraints: {}
 *     },
 *     tenantId: 'your-tenant-id'
 *   });
 *   
 *   // Legacy mandates (DEPRECATED - AP2 only)
 *   const mandate = await client.mandates.create({
 *     vcJwt: '...',
 *     tenantId: '...'
 *   });
 */

export { MandateVaultClient } from './client';
export * from './types';
export * from './errors';

export const VERSION = '1.0.0';

