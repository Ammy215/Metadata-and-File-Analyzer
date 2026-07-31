/**
 * Extract a user-facing message from an axios error, shared across every
 * page instead of each one redefining its own copy.
 */
export function getErrorMessage(error, fallback = 'Something went wrong') {
  // No response at all (network failure, connection refused, DNS/timeout)
  // or a 502/503/504 from nginx - both mean "the backend isn't answering
  // right now," most commonly because it's still starting up right after
  // a deploy/restart (confirmed empirically: a several-second window where
  // nginx serves the frontend fine but the backend isn't ready yet).
  // That's not the same as a rejected request, so it gets its own message
  // instead of a misleading "Login failed"-style fallback.
  if (!error.response || [502, 503, 504].includes(error.response.status)) {
    return 'Cannot reach the server right now. It may still be starting up - please try again in a few seconds.';
  }

  const data = error.response.data;

  // FastAPI/Pydantic validation errors: {"detail": [{"msg": "..."}, ...]}
  if (Array.isArray(data?.detail) && data.detail[0]?.msg) {
    return data.detail[0].msg;
  }

  return data?.error || data?.detail || fallback;
}
