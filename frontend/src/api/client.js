import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.error || err.message;
    console.error("[Axiom API]", msg);
    return Promise.reject(err);
  }
);

// ── Knowledge ────────────────────────────────────────────────────────────────
export const uploadDocument = (userId, file, halfLifeDays) => {
  const form = new FormData();
  form.append("file", file);
  if (halfLifeDays != null) form.append("half_life_days", String(halfLifeDays));
  return api.post(`/knowledge/upload?user_id=${userId}`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const listTopics = (userId) =>
  api.get(`/knowledge/topics?user_id=${userId}`);

export const getTopic = (topicId) =>
  api.get(`/knowledge/topics/${topicId}`);

export const deleteTopic = (topicId) =>
  api.delete(`/knowledge/topics/${topicId}`);

export const recordReview = (topicId, userId, durationMinutes = 30) =>
  api.post(`/knowledge/topics/${topicId}/review?user_id=${userId}`, {
    duration_minutes: durationMinutes,
  });

export const recalculateDecay = (userId) =>
  api.post(`/knowledge/decay/recalculate?user_id=${userId}`);

export const getKnowledgeGraph = (userId) =>
  api.get(`/knowledge/graph?user_id=${userId}`);

// ── Calendar ──────────────────────────────────────────────────────────────────
export const listEvents = (userId, start, end) => {
  const params = new URLSearchParams({ user_id: userId });
  if (start) params.append("start", start);
  if (end) params.append("end", end);
  return api.get(`/calendar/events?${params}`);
};

export const createEvent = (userId, eventData) =>
  api.post(`/calendar/events?user_id=${userId}`, eventData);

export const updateEvent = (eventId, eventData) =>
  api.put(`/calendar/events/${eventId}`, eventData);

export const deleteEvent = (eventId) =>
  api.delete(`/calendar/events/${eventId}`);

export const completeEvent = (eventId, userId) =>
  api.post(`/calendar/events/${eventId}/complete?user_id=${userId}`);

// ── Scheduling ────────────────────────────────────────────────────────────────
export const analyzeAndPropose = (userId) =>
  api.post(`/scheduling/analyze?user_id=${userId}`);

export const listProposals = (userId, status) => {
  const params = new URLSearchParams({ user_id: userId });
  if (status) params.append("status", status);
  return api.get(`/scheduling/proposals?${params}`);
};

export const acceptProposal = (proposalId) =>
  api.post(`/scheduling/proposals/${proposalId}/accept`);

export const declineProposal = (proposalId) =>
  api.post(`/scheduling/proposals/${proposalId}/decline`);

export const chatProposal = (proposalId, messages, message) =>
  api.post(`/scheduling/proposals/${proposalId}/chat`, {
    messages,
    message,
    now: new Date().toISOString(),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    utc_offset_minutes: -new Date().getTimezoneOffset(),
  });

export const applyProposalChanges = (proposalId, changes) =>
  api.post(`/scheduling/proposals/${proposalId}/apply`, { changes });
