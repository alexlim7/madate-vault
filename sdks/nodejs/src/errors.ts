/**
 * Error classes.
 */
import { AxiosError } from 'axios';

export class MandateVaultError extends Error {
  constructor(
    message: string,
    public statusCode?: number
  ) {
    super(message);
    this.name = 'MandateVaultError';
  }
}

export class AuthenticationError extends MandateVaultError {
  constructor(message: string) {
    super(message, 401);
    this.name = 'AuthenticationError';
  }
}

export class ValidationError extends MandateVaultError {
  constructor(message: string, statusCode?: number) {
    super(message, statusCode || 400);
    this.name = 'ValidationError';
  }
}

export class NotFoundError extends MandateVaultError {
  constructor(message: string) {
    super(message, 404);
    this.name = 'NotFoundError';
  }
}

export class RateLimitError extends MandateVaultError {
  constructor(
    message: string,
    public retryAfter?: number
  ) {
    super(message, 429);
    this.name = 'RateLimitError';
  }
}

export class ServerError extends MandateVaultError {
  constructor(message: string, statusCode?: number) {
    super(message, statusCode || 500);
    this.name = 'ServerError';
  }
}

export function handleAxiosError(error: AxiosError): Error {
  const status = error.response?.status;
  const message = (error.response?.data as any)?.detail || error.message;
  
  if (status === 401) {
    return new AuthenticationError(message);
  } else if (status === 400 || status === 422) {
    return new ValidationError(message, status);
  } else if (status === 404) {
    return new NotFoundError(message);
  } else if (status === 429) {
    const retryAfter = error.response?.headers['retry-after'];
    return new RateLimitError(message, retryAfter ? parseInt(retryAfter) : undefined);
  } else if (status && status >= 500) {
    return new ServerError(message, status);
  }
  
  return new MandateVaultError(message, status);
}

