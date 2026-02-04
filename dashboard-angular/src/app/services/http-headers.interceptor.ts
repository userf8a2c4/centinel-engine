import { HttpEvent, HttpHandler, HttpInterceptor, HttpRequest } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

/**
 * Interceptor para headers persistentes del cliente.
 * Interceptor for persistent client headers.
 */
@Injectable()
export class HttpHeadersInterceptor implements HttpInterceptor {
  /**
   * Clona la request con headers adicionales para trazabilidad.
   * Clones the request with additional headers for traceability.
   */
  intercept(
    req: HttpRequest<unknown>,
    next: HttpHandler
  ): Observable<HttpEvent<unknown>> {
    const cloned = req.clone({
      setHeaders: {
        'X-Observer-Client': environment.clientName,
        'X-Client-User-Agent': environment.clientUserAgent,
      },
    });

    return next.handle(cloned);
  }
}
