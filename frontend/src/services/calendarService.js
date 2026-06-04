import * as apiClient from "../api/client";

/**
 * Calendar service abstraction.
 *
 * DIP seam: high-level UI components depend on this domain-level interface, not
 * on axios or the raw HTTP error shapes. It translates transport responses into
 * explicit domain results so the UI never has to know an HTTP 409 means
 * "overlap". A different implementation (mock, offline, alternate transport)
 * can be injected without touching the components.
 *
 * createEvent resolves to a discriminated result instead of throwing:
 *   { ok: true,  event }
 *   { ok: false, reason: "conflict", conflicts, message }
 *   { ok: false, reason: "error",    message }
 */
export function createCalendarService(client = apiClient) {
  return {
    listEvents: (userId, start, end) => client.listEvents(userId, start, end),

    deleteEvent: (eventId) => client.deleteEvent(eventId),

    completeEvent: (eventId, userId) => client.completeEvent(eventId, userId),

    async createEvent(userId, eventData) {
      try {
        const { data } = await client.createEvent(userId, eventData);
        return { ok: true, event: data };
      } catch (err) {
        return toFailure(err, "create");
      }
    },

    async updateEvent(eventId, eventData) {
      try {
        const { data } = await client.updateEvent(eventId, eventData);
        return { ok: true, event: data };
      } catch (err) {
        return toFailure(err, "update");
      }
    },
  };
}

function toFailure(err, verb) {
  const status = err.response?.status;
  const body = err.response?.data || {};
  if (status === 409) {
    return {
      ok: false,
      reason: "conflict",
      conflicts: body.conflicts || [],
      message: body.error || "This time overlaps an existing event.",
    };
  }
  if (status === 422 && body.errors) {
    return {
      ok: false,
      reason: "validation",
      conflicts: [],
      message: flattenValidationErrors(body.errors) || `Could not ${verb} event.`,
    };
  }
  return {
    ok: false,
    reason: "error",
    conflicts: [],
    message: body.error || err.message || `Could not ${verb} event.`,
  };
}

// Marshmallow returns errors as { field: [msg, ...], _schema: [msg, ...] }
// (fields may nest further). Flatten every message into one readable string.
function flattenValidationErrors(errors) {
  const messages = [];
  const walk = (node) => {
    if (Array.isArray(node)) node.forEach(walk);
    else if (node && typeof node === "object") Object.values(node).forEach(walk);
    else if (node) messages.push(String(node));
  };
  walk(errors);
  return messages.join(" ");
}

// Default singleton wired to the real API client.
export const calendarService = createCalendarService();
