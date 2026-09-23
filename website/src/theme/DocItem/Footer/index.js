import Footer from '@theme-original/DocItem/Footer';
import PageFeedback from '@site/src/components/PageFeedback';

/**
 * Wrap-swizzle of DocItem/Footer. Keeps the default footer (edit link,
 * last-updated stamp) and adds the page feedback prompt below it.
 */
export default function FooterWrapper(props) {
  return (
    <>
      <Footer {...props} />
      <PageFeedback />
    </>
  );
}
