const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Generic fetch wrapper with error handling and request correlation support
 */
async function fetchApi(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    const requestId = response.headers.get('X-Request-ID') || 'N/A';

    if (!response.ok) {
      let errorDetail = `HTTP error status ${response.status}`;
      try {
        const errorJson = await response.json();
        if (errorJson.detail) {
          errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
        }
      } catch (e) {
        // Fallback to text error detail
      }
      return {
        success: false,
        status: response.status,
        requestId,
        error: errorDetail,
      };
    }

    const data = await response.json();
    return {
      success: true,
      status: response.status,
      requestId,
      data,
    };
  } catch (error) {
    return {
      success: false,
      status: 0,
      requestId: 'N/A',
      error: error.message || 'Network connection failed. Ensure FastAPI backend is running.',
    };
  }
}

// 1. System Health & Readiness
export function getHealthStatus() {
  return fetchApi('/health');
}

export function getReadinessStatus() {
  return fetchApi('/ready');
}

// 2. Substitution Decision Engine Evaluation & Preset Lookup
export function evaluateSubstitution(payload) {
  return fetchApi('/api/v1/substitutions/evaluate', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function lookupPreset(patientCode, prescriptionCode) {
  return fetchApi(`/api/v1/substitutions/preset-lookup/${patientCode}/${prescriptionCode}`);
}

// 3. Persisted Decision Detail View
export function getDecisionDetails(decisionId) {
  return fetchApi(`/api/v1/substitutions/${decisionId}`);
}

// 4. Pharmacist Human-in-the-Loop Review Submission
export function submitPharmacistReview(decisionId, reviewPayload, pharmacistToken = 'PHARM-TOKEN-101') {
  return fetchApi(`/api/v1/substitutions/${decisionId}/review`, {
    method: 'POST',
    headers: {
      'X-Pharmacist-Token': pharmacistToken,
    },
    body: JSON.stringify(reviewPayload),
  });
}

// 5. Filtered Decision History with Pagination
export function getDecisionHistory(params = {}) {
  const queryParams = new URLSearchParams();
  if (params.patient_id) queryParams.append('patient_id', params.patient_id);
  if (params.decision_status) queryParams.append('decision_status', params.decision_status);
  if (params.risk_level) queryParams.append('risk_level', params.risk_level);
  if (params.limit !== undefined) queryParams.append('limit', params.limit);
  if (params.offset !== undefined) queryParams.append('offset', params.offset);

  const queryString = queryParams.toString();
  const endpoint = `/api/v1/substitutions${queryString ? `?${queryString}` : ''}`;
  return fetchApi(endpoint);
}

// 6. Analytics Dashboard Summary
export function getAnalyticsSummary() {
  return fetchApi('/api/v1/substitutions/analytics/summary');
}

// 7. Synthetic Population Demographic Fairness Metrics
export function getFairnessMetrics() {
  return fetchApi('/api/v1/substitutions/analytics/fairness');
}

// 8. Safety Audit & Error Analysis Metrics
export function getErrorAnalysisMetrics() {
  return fetchApi('/api/v1/substitutions/analytics/error-analysis');
}
