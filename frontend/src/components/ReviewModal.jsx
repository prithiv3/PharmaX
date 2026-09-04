import React, { useState } from 'react';
import { submitPharmacistReview } from '../services/api';

export default function ReviewModal({ decisionId, initialStatus, pharmacistToken, onClose, onSuccess }) {
  const [reviewStatus, setReviewStatus] = useState('APPROVED');
  const [pharmacistCode, setPharmacistCode] = useState('PHARM-101');
  const [reviewNotes, setReviewNotes] = useState('');
  const [overrideReason, setOverrideReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const isOverride = reviewStatus === 'OVERRIDDEN';

  async function handleSubmit(e) {
    e.preventDefault();
    setErrorMessage(null);

    // Client-side validation: OVERRIDDEN requires non-empty override_reason
    if (isOverride && (!overrideReason || !overrideReason.trim())) {
      setErrorMessage('An explicit override reason is required when selecting OVERRIDDEN status.');
      return;
    }

    setIsSubmitting(true);
    const payload = {
      pharmacist_code: pharmacistCode.trim() || 'PHARM-101',
      review_status: reviewStatus,
      review_notes: reviewNotes.trim() || undefined,
      override_reason: isOverride ? overrideReason.trim() : undefined,
    };

    const res = await submitPharmacistReview(decisionId, payload, pharmacistToken);
    setIsSubmitting(false);

    if (res.success) {
      onSuccess(res.data);
      onClose();
    } else {
      setErrorMessage(res.error || 'Failed to submit pharmacist review. Verify authorization token.');
    }
  }

  return (
    <div className="modal-backdrop">
      <div className="modal-card">
        <div className="modal-header">
          <h2>Submit Pharmacist Review (Decision #{decisionId})</h2>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        {errorMessage && (
          <div className="alert alert-danger">
            <strong>Review Submission Error:</strong> {errorMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} className="review-form">
          <div className="form-group">
            <label>Pharmacist Code:</label>
            <input
              type="text"
              className="form-control"
              value={pharmacistCode}
              onChange={(e) => setPharmacistCode(e.target.value)}
              placeholder="e.g. PHARM-101"
              required
            />
          </div>

          <div className="form-group">
            <label>Review Decision Status:</label>
            <div className="radio-group">
              <label className={`radio-label ${reviewStatus === 'APPROVED' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="status"
                  value="APPROVED"
                  checked={reviewStatus === 'APPROVED'}
                  onChange={() => setReviewStatus('APPROVED')}
                />
                Approve Substitution
              </label>

              <label className={`radio-label ${reviewStatus === 'REJECTED' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="status"
                  value="REJECTED"
                  checked={reviewStatus === 'REJECTED'}
                  onChange={() => setReviewStatus('REJECTED')}
                />
                Reject Substitution
              </label>

              <label className={`radio-label ${reviewStatus === 'OVERRIDDEN' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="status"
                  value="OVERRIDDEN"
                  checked={reviewStatus === 'OVERRIDDEN'}
                  onChange={() => setReviewStatus('OVERRIDDEN')}
                />
                Clinical Override (Requires Reason)
              </label>
            </div>
          </div>

          {isOverride && (
            <div className="form-group override-group">
              <label className="required-label">Override Reason (Mandatory):</label>
              <textarea
                className="form-control"
                rows="3"
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                placeholder="Detail clinical justification for overriding safety block (e.g. Desensitization completed, specialist authorization)..."
                required
              ></textarea>
            </div>
          )}

          <div className="form-group">
            <label>Review Notes (Optional):</label>
            <input
              type="text"
              className="form-control"
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              placeholder="Internal pharmacy notes..."
            />
          </div>

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
              {isSubmitting ? 'Submitting Review...' : 'Submit Review'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
