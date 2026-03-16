import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';

export default function NotFound() {
  return (
    <Layout title="Page Not Found">
      <main className="not-found">
        <h1 className="not-found__code">404</h1>
        <p className="not-found__title">
          This page wandered off the jobsite.
        </p>
        <p className="not-found__desc">
          The page you're looking for doesn't exist or has been moved. Let's get
          you back on track.
        </p>
        <div className="not-found__buttons">
          <Link
            className="button button--lg button--accent"
            to="/">
            Back to Home
          </Link>
          <Link
            className="button button--lg button--outline button--secondary"
            to="/docs/intro">
            Read the Docs
          </Link>
        </div>
      </main>
    </Layout>
  );
}
