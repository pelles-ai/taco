import {useEffect, useState} from 'react';
import {useLocation} from '@docusaurus/router';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';

const REPO = 'https://github.com/pelles-ai/taco';

/**
 * "Was this page helpful?" prompt at the foot of every docs page.
 *
 * There is no feedback backend, so the widget never pretends to send
 * anything. "No" routes the reader to a prefilled GitHub issue, which is
 * where docs fixes are tracked; "Yes" says thanks and points to
 * Discussions for anything they want to add.
 */
export default function PageFeedback() {
  const {pathname} = useLocation();
  const {siteConfig} = useDocusaurusContext();
  const [vote, setVote] = useState(null);

  // Reset when the reader navigates to another page.
  useEffect(() => setVote(null), [pathname]);

  const pageUrl = `${siteConfig.url}${pathname}`;
  const issueUrl =
    `${REPO}/issues/new?labels=docs` +
    `&title=${encodeURIComponent(`Docs: ${pathname}`)}` +
    `&body=${encodeURIComponent(
      `Page: ${pageUrl}\n\nWhat was missing, wrong or confusing:\n\n`,
    )}`;

  return (
    <aside className="page-feedback" aria-label="Page feedback">
      {vote === null ? (
        <>
          <span className="page-feedback__prompt">Was this page helpful?</span>
          <div className="page-feedback__buttons">
            <button type="button" className="page-feedback__btn" onClick={() => setVote('up')}>
              Yes
            </button>
            <button type="button" className="page-feedback__btn" onClick={() => setVote('down')}>
              No
            </button>
          </div>
        </>
      ) : vote === 'up' ? (
        <p className="page-feedback__reply" role="status">
          Thanks. Anything to add?{' '}
          <a href={`${REPO}/discussions`} target="_blank" rel="noopener noreferrer">
            Start a discussion
          </a>
          .
        </p>
      ) : (
        <p className="page-feedback__reply" role="status">
          Tell us what to fix and we will track it:{' '}
          <a href={issueUrl} target="_blank" rel="noopener noreferrer">
            open a docs issue for this page
          </a>
          . It opens GitHub with the page link filled in.
        </p>
      )}
    </aside>
  );
}
