/**
 * Mandate resource.
 */
import { AxiosInstance } from 'axios';
import { Mandate, MandateSearchParams, MandateSearchResults } from '../types';

export class Mandates {
  constructor(private http: AxiosInstance) {}
  
  /**
   * Create a new mandate.
   */
  async create(params: {
    vcJwt: string;
    tenantId: string;
    retentionDays?: number;
  }): Promise<Mandate> {
    const response = await this.http.post('/api/v1/mandates', {
      vc_jwt: params.vcJwt,
      tenant_id: params.tenantId,
      retention_days: params.retentionDays || 90
    });
    
    return response.data;
  }
  
  /**
   * Get mandate by ID.
   */
  async get(mandateId: string): Promise<Mandate> {
    const response = await this.http.get(`/api/v1/mandates/${mandateId}`);
    return response.data;
  }
  
  /**
   * Search mandates.
   */
  async search(params: MandateSearchParams): Promise<MandateSearchResults> {
    const response = await this.http.post('/api/v1/mandates/search', {
      tenant_id: params.tenantId,
      issuer_did: params.issuerDid,
      subject_did: params.subjectDid,
      status: params.status,
      limit: params.limit || 50,
      offset: params.offset || 0
    });
    
    return response.data;
  }
  
  /**
   * Revoke a mandate.
   */
  async revoke(mandateId: string): Promise<Mandate> {
    const response = await this.http.delete(`/api/v1/mandates/${mandateId}`);
    return response.data;
  }
}

