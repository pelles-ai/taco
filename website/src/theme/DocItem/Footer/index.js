import Footer from '@theme-original/DocItem/Footer';
import PageFeedback from '@site/src/components/PageFeedback';

/**
 * Wraps the default DocItem/Footer (which renders the Edit-this-page,
 * Last-updated, and prev/next pagination) and appends the page feedback
 * widget below it. Wrap-swizzle pattern — we don't replace the default,
 * we extend it.
 */
export default function FooterWrapper(props) {
  return (
    <>
      <Footer {...props} />
      <PageFeedback />
    </>
  );
}
