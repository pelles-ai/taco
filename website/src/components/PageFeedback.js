import {useCallback, useEffect, useState} from 'react';
import BrowserOnly from '@docusaurus/BrowserOnly';

/**
 * "Was this page helpful?" widget.
 *
 * Local-only persistence today (per-page in localStorage). The hooks are
 * already in place to wire a real backend later (POST to a collect
 * endpoint, anon-id via a UUID in localStorage). For now the value is
 * visible: lets visitors give signal, lets us count it client-side.
 */

const STORAGE_PREFIX = 'taco-feedback:';
const SUBMITTED_PREFIX = 'taco-feedback-submitted:';

function pageKey() {
  if (typeof window === 'undefined') return '';
  return STORAGE_PREFIX + window.location.pathname;
}
function submittedKey() {
  if (typeof window === 'undefined') return '';
  return SUBMITTED_PREFIX + window.location.pathname;
}

function Inner() {
  const [vote, setVote] = useState(null); // 'up' | 'down' | null
  const [comment, setComment] = useState('');
  const [submitted, setSubmitted] = useState(false);

  // On route change, reset and rehydrate from localStorage
  useEffect(() => {
    const handler = () => {
      try {
        const stored = localStorage.getItem(pageKey());
        const sub = localStorage.getItem(submittedKey());
        if (sub) {
          const data = JSON.parse(sub);
          setVote(data.vote);
          setComment(data.comment ?? '');
          setSubmitted(true);
        } else if (stored) {
          const data = JSON.parse(stored);
          setVote(data.vote);
          setComment(data.comment ?? '');
          setSubmitted(false);
        } else {
          setVote(null);
          setComment('');
          setSubmitted(false);
        }
      } catch (_) {
        setVote(null);
        setComment('');
        setSubmitted(false);
      }
    };
    handler();
    window.addEventListener('popstate', handler);
    return () => window.removeEventListener('popstate', handler);
  }, []);

  const choose = useCallback((v) => {
    setVote(v);
    try {
      localStorage.setItem(pageKey(), JSON.stringify({vote: v}));
    } catch (_) {}
  }, []);

  const submit = useCallback(() => {
    const payload = {
      vote,
      comment: comment.trim() || null,
      url: window.location.pathname,
      at: new Date().toISOString(),
    };
    try {
      localStorage.setItem(submittedKey(), JSON.stringify(payload));
      localStorage.removeItem(pageKey());
    } catch (_) {}
    // TODO: when a backend is available, POST(payload) here.
    setSubmitted(true);
  }, [vote, comment]);

  if (submitted) {
    return (
      <div className="page-feedback page-feedback--done">
        <span className="page-feedback__done-glyph">✓</span>
        Thanks for the feedback.
      </div>
    );
  }

  return (
    <div className="page-feedback">
      <div className="page-feedback__prompt">Was this page helpful?</div>
      <div className="page-feedback__vote-row">
        <button
          type="button"
          className={`page-feedback__vote ${vote === 'up' ? 'page-feedback__vote--active page-feedback__vote--up' : ''}`}
          onClick={() => choose('up')}
          aria-label="Yes, this page was helpful"
          aria-pressed={vote === 'up'}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M7 22V11M2 13v7a2 2 0 002 2h3M7 11V5a3 3 0 013-3l3 9h6a2 2 0 012 2l-1 9a2 2 0 01-2 2H7" />
          </svg>
          Yes
        </button>
        <button
          type="button"
          className={`page-feedback__vote ${vote === 'down' ? 'page-feedback__vote--active page-feedback__vote--down' : ''}`}
          onClick={() => choose('down')}
          aria-label="No, this page was not helpful"
          aria-pressed={vote === 'down'}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M17 2v11M22 11V4a2 2 0 00-2-2h-3M17 13v6a3 3 0 01-3 3l-3-9H5a2 2 0 01-2-2l1-9a2 2 0 012-2h10" />
          </svg>
          No
        </button>
      </div>

      {vote ? (
        <div className="page-feedback__detail">
          <label htmlFor="page-feedback-comment" className="page-feedback__label">
            {vote === 'up' ? 'What worked? (optional)' : 'What was missing or confusing? (optional)'}
          </label>
          <textarea
            id="page-feedback-comment"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder={vote === 'up' ? 'A specific example helps.' : 'A specific gap helps us prioritize.'}
            rows={3}
          />
          <button
            type="button"
            className="page-feedback__submit"
            onClick={submit}>
            Send feedback
          </button>
        </div>
      ) : null}
    </div>
  );
}

export default function PageFeedback() {
  return <BrowserOnly fallback={null}>{() => <Inner />}</BrowserOnly>;
}
