/**
 * Authorization resource (multi-protocol: AP2 + ACP).
 * 
 * This is the modern API for managing authorizations.
 * Supports both AP2 (JWT-VC) and ACP (Delegated Token) protocols.
 */
import { AxiosInstance } from 'axios';
import { Authorization, AuthorizationSearchParams, AuthorizationSearchResults } from '../types';

export class Authorizations {
  constructor(private http: AxiosInstance) {}
  
  /**
   * Create a new authorization (AP2 or ACP).
   * 
   * @example AP2 (JWT-VC)
   * ```typescript
   * const auth = await client.authorizations.create({
   *   protocol: 'AP2',
   *   payload: { vcJwt: 'eyJhbGc...' },
   *   tenantId: 'tenant-123'
   * });
   * ```
   * 
   * @example ACP (Delegated Token)
   * ```typescript
   * const auth = await client.authorizations.create({
   *   protocol: 'ACP',
   *   payload: {
   *     tokenId: 'acp-token-123',
   *     pspId: 'psp-stripe',
   *     merchantId: 'merchant-456',
   *     maxAmount: '5000.00',
   *     currency: 'USD',
   *     expiresAt: '2026-01-01T00:00:00Z',
   *     constraints: {}
   *   },
   *   tenantId: 'tenant-123'
   * });
   * ```
   */
  async create(params: {
    protocol: 'AP2' | 'ACP';
    payload: any;
    tenantId: string;
    retentionDays?: number;
  }): Promise<Authorization> {
    const response = await this.http.post('/api/v1/authorizations/', {
      protocol: params.protocol,
      payload: params.payload,
      tenant_id: params.tenantId,
      retention_days: params.retentionDays || 90
    });
    
    return response.data;
  }
  
  /**
   * Get authorization by ID.
   */
  async get(authorizationId: string): Promise<Authorization> {
    const response = await this.http.get(`/api/v1/authorizations/${authorizationId}`);
    return response.data;
  }
  
  /**
   * Re-verify an existing authorization.
   */
  async verify(authorizationId: string): Promise<{
    id: string;
    protocol: string;
    status: string;
    reason: string;
    expiresAt?: string;
    amountLimit?: number;
    currency?: string;
  }> {
    const response = await this.http.post(`/api/v1/authorizations/${authorizationId}/verify`, {});
    return response.data;
  }
  
  /**
   * Search authorizations with advanced filters.
   * 
   * @example
   * ```typescript
   * const results = await client.authorizations.search({
   *   tenantId: 'tenant-123',
   *   protocol: 'ACP',
   *   status: 'VALID',
   *   currency: 'USD',
   *   minAmount: '1000.00',
   *   limit: 50
   * });
   * 
   * console.log(`Found ${results.total} authorizations`);
   * results.authorizations.forEach(auth => {
   *   console.log(`  ${auth.id}: ${auth.protocol} - ${auth.status}`);
   * });
   * ```
   */
  async search(params: AuthorizationSearchParams): Promise<AuthorizationSearchResults> {
    const requestBody: any = {
      tenant_id: params.tenantId,
      limit: params.limit || 50,
      offset: params.offset || 0,
      sort_by: params.sortBy || 'created_at',
      sort_order: params.sortOrder || 'desc'
    };
    
    // Add optional filters
    if (params.protocol) requestBody.protocol = params.protocol;
    if (params.issuer) requestBody.issuer = params.issuer;
    if (params.subject) requestBody.subject = params.subject;
    if (params.status) requestBody.status = params.status;
    if (params.expiresBefore) requestBody.expires_before = params.expiresBefore;
    if (params.expiresAfter) requestBody.expires_after = params.expiresAfter;
    if (params.minAmount) requestBody.min_amount = params.minAmount;
    if (params.maxAmount) requestBody.max_amount = params.maxAmount;
    if (params.currency) requestBody.currency = params.currency;
    
    const response = await this.http.post('/api/v1/authorizations/search', requestBody);
    return response.data;
  }
  
  /**
   * Revoke an authorization.
   */
  async revoke(authorizationId: string): Promise<Authorization> {
    const response = await this.http.delete(`/api/v1/authorizations/${authorizationId}`);
    return response.data;
  }
  
  /**
   * Export evidence pack as ZIP file.
   * 
   * @example
   * ```typescript
   * const zipBuffer = await client.authorizations.exportEvidencePack('auth-123');
   * fs.writeFileSync('./evidence_pack.zip', zipBuffer);
   * ```
   */
  async exportEvidencePack(authorizationId: string): Promise<Buffer> {
    const response = await this.http.get(
      `/api/v1/authorizations/${authorizationId}/evidence-pack`,
      { responseType: 'arraybuffer' }
    );
    
    return Buffer.from(response.data);
  }
}


