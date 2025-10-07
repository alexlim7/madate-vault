/**
 * TypeScript type definitions.
 */

/**
 * Authorization (multi-protocol: AP2 + ACP).
 */
export interface Authorization {
  id: string;
  protocol: 'AP2' | 'ACP';
  issuer: string;  // DID for AP2, PSP ID for ACP
  subject: string;  // DID for AP2, Merchant ID for ACP
  scope?: Record<string, any>;
  amount_limit?: string;
  currency?: string;
  expires_at: string;
  status: 'VALID' | 'EXPIRED' | 'REVOKED' | 'ACTIVE';
  verification_status?: string;
  verification_reason?: string;
  verified_at?: string;
  tenant_id: string;
  created_at: string;
  updated_at: string;
}

/**
 * Authorization search parameters.
 */
export interface AuthorizationSearchParams {
  tenantId: string;
  protocol?: 'AP2' | 'ACP';
  issuer?: string;
  subject?: string;
  status?: string;
  expiresBefore?: string;
  expiresAfter?: string;
  minAmount?: string;
  maxAmount?: string;
  currency?: string;
  limit?: number;
  offset?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

/**
 * Authorization search results.
 */
export interface AuthorizationSearchResults {
  authorizations: Authorization[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Mandate (DEPRECATED - use Authorization instead).
 * 
 * @deprecated Use Authorization interface for new code.
 */
export interface Mandate {
  id: string;
  vc_jwt: string;
  issuer_did: string;
  subject_did: string;
  scope: string;
  amount_limit?: string;
  expires_at?: string;
  status: string;
  verification_status: string;
  verification_reason?: string;
  tenant_id: string;
  created_at: string;
  updated_at: string;
}

export interface MandateSearchParams {
  tenantId: string;
  issuerDid?: string;
  subjectDid?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

export interface MandateSearchResults {
  mandates: Mandate[];
  total: number;
  limit: number;
  offset: number;
}

export interface Webhook {
  id: string;
  name: string;
  url: string;
  events: string[];
  is_active: boolean;
  tenant_id: string;
  created_at: string;
}

export interface AuditLog {
  id: string;
  mandate_id?: string;
  event_type: string;
  timestamp: string;
  details: Record<string, any>;
}

