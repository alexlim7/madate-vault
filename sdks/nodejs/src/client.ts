/**
 * Main client for Mandate Vault API.
 */
import axios, { AxiosInstance, AxiosError } from 'axios';
import { Mandates } from './resources/mandates';
import { Webhooks } from './resources/webhooks';
import { Audit } from './resources/audit';
import { MandateVaultError, handleAxiosError } from './errors';

export interface ClientConfig {
  apiKey: string;
  baseUrl?: string;
  timeout?: number;
}

export class MandateVaultClient {
  private http: AxiosInstance;
  
  public readonly mandates: Mandates;
  public readonly webhooks: Webhooks;
  public readonly audit: Audit;
  
  constructor(config: ClientConfig) {
    if (!config.apiKey || !config.apiKey.startsWith('mvk_')) {
      throw new Error("Invalid API key. Must start with 'mvk_'");
    }
    
    const baseUrl = config.baseUrl || 'https://api.mandatevault.com';
    const timeout = config.timeout || 30000;
    
    this.http = axios.create({
      baseURL: baseUrl,
      timeout,
      headers: {
        'X-API-Key': config.apiKey,
        'Content-Type': 'application/json',
        'User-Agent': 'mandate-vault-nodejs/1.0.0'
      }
    });
    
    // Add error interceptor
    this.http.interceptors.response.use(
      response => response,
      (error: AxiosError) => {
        throw handleAxiosError(error);
      }
    );
    
    // Initialize resources
    this.mandates = new Mandates(this.http);
    this.webhooks = new Webhooks(this.http);
    this.audit = new Audit(this.http);
  }
}

