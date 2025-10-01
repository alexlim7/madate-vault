/**
 * TypeScript type definitions.
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

