/**
 * Error helpers: map HTTP status → user-friendly copy per contract/api-endpoints.md
 */

export function getErrorMessage(status: number, detail?: string): string {
  switch (status) {
    case 400:
      return detail || "Invalid request.";
    case 401:
      return "Session expired — please sign in again";
    case 403:
      return "You don't have access to this resource";
    case 404:
      return "Resource not found";
    case 409:
      return detail || "This item already exists";
    case 422:
      return detail || "Please check your input";
    case 429:
      return "Rate limited — please try again later";
    case 500:
    case 502:
    case 503:
    case 504:
      return "Something went wrong. Please try again.";
    default:
      if (detail) return detail;
      return "Something went wrong. Please try again.";
  }
}

export function shouldRedirectToLogin(status: number): boolean {
  return status === 401;
}

export function getRetryAfterMessage(retryAfter?: string): string {
  if (!retryAfter) return "Rate limited — please try again later";
  const seconds = parseInt(retryAfter, 10);
  if (isNaN(seconds)) return "Rate limited — please try again later";
  if (seconds < 60) return `Rate limited — try again in ${seconds} seconds`;
  const minutes = Math.ceil(seconds / 60);
  return `Rate limited — try again in ${minutes} minute${minutes > 1 ? "s" : ""}`;
}
