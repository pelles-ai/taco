/**
 * Per-page Open Graph image generator.
 *
 * Renders one PNG per docs/blog/pages route during postBuild using Satori +
 * Sharp, writes it to build/img/og/{hash}.png, and injects a per-page
 * <meta property="og:image"> into the corresponding index.html.
 */

const path = require('node:path');
const fs = require('node:fs/promises');
const crypto = require('node:crypto');

const FONT_REG = path.resolve(
  __dirname,
  '../../node_modules/@fontsource/inter/files/inter-latin-400-normal.woff',
);
const FONT_BOLD = path.resolve(
  __dirname,
  '../../node_modules/@fontsource/inter/files/inter-latin-700-normal.woff',
);

const W = 1200;
const H = 630;

const NAVY = '#06090f';
const NAVY_DEEP = '#02050a';
const GOLD = '#EAB308';
const TEXT = '#f1f5f9';
const TEXT_DIM = 'rgba(241, 245, 249, 0.62)';
const HAIRLINE = 'rgba(255, 255, 255, 0.08)';

function deriveSection(routePath) {
  if (routePath === '/' || routePath === '/index.html') return 'TACO';
  if (routePath.startsWith('/docs/cookbook')) return 'Cookbook';
  if (routePath.startsWith('/docs/sdk-reference')) return 'SDK Reference';
  if (routePath.startsWith('/docs/schemas')) return 'Data Schemas';
  if (routePath.startsWith('/docs/getting-started')) return 'Getting Started';
  if (routePath.startsWith('/docs/case-studies')) return 'Case Study';
  if (routePath.startsWith('/docs/decisions')) return 'Architecture Decision';
  if (routePath.startsWith('/docs/spec')) return 'Specification';
  if (routePath.startsWith('/docs/')) return 'Documentation';
  if (routePath.startsWith('/for/general-contractor')) return 'For General Contractors';
  if (routePath.startsWith('/for/owner')) return 'For Owners';
  if (routePath.startsWith('/for/subcontractor')) return 'For Subcontractors';
  if (routePath.startsWith('/for/platform-vendor')) return 'For Platform Vendors';
  if (routePath.startsWith('/for/mechanical')) return 'For Mechanical Trades';
  if (routePath.startsWith('/for/electrical')) return 'For Electrical Trades';
  if (routePath.startsWith('/for/plumbing')) return 'For Plumbing Trades';
  if (routePath.startsWith('/for/structural')) return 'For Structural Trades';
  if (routePath.startsWith('/for/')) return 'By Role';
  if (routePath.startsWith('/blog')) return 'Blog';
  if (routePath.startsWith('/sandbox')) return 'Sandbox';
  if (routePath.startsWith('/conformance')) return 'Conformance';
  return 'TACO';
}

function extractTitle(html, routePath) {
  const og = /<meta[^>]+property=["']og:title["'][^>]+content=["']([^"']+)/i.exec(html);
  if (og) return clean(og[1]);
  const t = /<title[^>]*>([^<]+)<\/title>/i.exec(html);
  if (t) return clean(t[1]);
  return clean(routePath.replace(/\W+/g, ' ').trim() || 'TACO');
}

function clean(s) {
  return s
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&#39;/g, "'")
    .replace(/&rarr;|&#8594;|→|⟶/g, '›')
    .replace(/&larr;|&#8592;|←/g, '‹')
    .replace(/\s*[|·]\s*TACO\s*$/i, '')
    .trim();
}

function shortHash(s) {
  return crypto.createHash('sha1').update(s).digest('hex').slice(0, 10);
}

function titleFontSize(title) {
  const len = title.length;
  if (len <= 24) return 84;
  if (len <= 40) return 72;
  if (len <= 60) return 60;
  if (len <= 80) return 50;
  return 42;
}

function ogElement({title, section}) {
  return {
    type: 'div',
    props: {
      style: {
        width: W,
        height: H,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        background: `linear-gradient(180deg, ${NAVY} 0%, ${NAVY_DEEP} 100%)`,
        padding: '72px',
        position: 'relative',
        fontFamily: 'Inter',
        color: TEXT,
      },
      children: [
        {
          type: 'div',
          props: {
            style: {
              position: 'absolute',
              top: -200,
              left: W / 2 - 360,
              width: 720,
              height: 480,
              background:
                'radial-gradient(ellipse, rgba(234, 179, 8, 0.18) 0%, transparent 60%)',
              display: 'flex',
            },
          },
        },
        {
          type: 'div',
          props: {
            style: {
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: 22,
            },
            children: [
              {
                type: 'div',
                props: {
                  style: {
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                  },
                  children: [
                    {
                      type: 'div',
                      props: {
                        style: {
                          width: 32,
                          height: 32,
                          borderRadius: 8,
                          background: GOLD,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: NAVY,
                          fontSize: 20,
                          fontWeight: 700,
                        },
                        children: 'T',
                      },
                    },
                    {
                      type: 'div',
                      props: {
                        style: {
                          fontWeight: 700,
                          letterSpacing: -0.5,
                          fontSize: 26,
                        },
                        children: 'TACO',
                      },
                    },
                  ],
                },
              },
              {
                type: 'div',
                props: {
                  style: {
                    fontSize: 18,
                    color: GOLD,
                    fontFamily: 'Inter',
                    fontWeight: 700,
                    letterSpacing: 1.4,
                    textTransform: 'uppercase',
                  },
                  children: section,
                },
              },
            ],
          },
        },
        {
          type: 'div',
          props: {
            style: {
              display: 'flex',
              flexDirection: 'column',
              gap: 24,
              maxWidth: W - 144,
            },
            children: [
              {
                type: 'div',
                props: {
                  style: {
                    fontSize: titleFontSize(title),
                    fontWeight: 700,
                    letterSpacing: -2,
                    lineHeight: 1.05,
                    color: TEXT,
                  },
                  children: title,
                },
              },
              {
                type: 'div',
                props: {
                  style: {
                    width: 96,
                    height: 4,
                    background: GOLD,
                    borderRadius: 999,
                  },
                },
              },
            ],
          },
        },
        {
          type: 'div',
          props: {
            style: {
              display: 'flex',
              alignItems: 'flex-end',
              justifyContent: 'space-between',
              borderTop: `1px solid ${HAIRLINE}`,
              paddingTop: 28,
              fontSize: 22,
            },
            children: [
              {
                type: 'div',
                props: {
                  style: {color: TEXT_DIM},
                  children: 'The A2A Construction Open-standard',
                },
              },
              {
                type: 'div',
                props: {
                  style: {
                    color: TEXT_DIM,
                    fontFamily: 'Inter',
                    fontSize: 20,
                    fontWeight: 700,
                  },
                  children: 'taco-protocol.com',
                },
              },
            ],
          },
        },
      ],
    },
  };
}

async function* walkIndexFiles(root, base = '/') {
  const entries = await fs.readdir(root, {withFileTypes: true});
  for (const e of entries) {
    const full = path.join(root, e.name);
    if (e.isDirectory()) {
      if (e.name === 'img' || e.name === 'assets' || e.name === 'fonts')
        continue;
      yield* walkIndexFiles(full, path.posix.join(base, e.name));
    } else if (e.isFile() && e.name === 'index.html') {
      yield {htmlPath: full, route: base === '/' ? '/' : base + '/'};
    }
  }
}

function patchOgMeta(html, imageUrl) {
  let out = html;
  const ogRe = /(<meta[^>]+property=["']og:image["'][^>]+content=["'])[^"']+/i;
  if (ogRe.test(out)) {
    out = out.replace(ogRe, `$1${imageUrl}`);
  }
  const twRe = /(<meta[^>]+name=["']twitter:image["'][^>]+content=["'])[^"']+/i;
  if (twRe.test(out)) {
    out = out.replace(twRe, `$1${imageUrl}`);
  } else {
    const head = /<\/head>/i;
    if (head.test(out)) {
      out = out.replace(
        head,
        `<meta name="twitter:image" content="${imageUrl}"><meta name="twitter:card" content="summary_large_image"></head>`,
      );
    }
  }
  return out;
}

module.exports = function ogImagesPlugin(_context, _options) {
  return {
    name: 'og-images',

    async postBuild({outDir, siteConfig}) {
      const {default: satori} = await import('satori');
      const {default: sharp} = await import('sharp');

      const [fontRegular, fontBold] = await Promise.all([
        fs.readFile(FONT_REG),
        fs.readFile(FONT_BOLD),
      ]);

      const ogDir = path.join(outDir, 'img', 'og');
      await fs.mkdir(ogDir, {recursive: true});

      const baseUrl = (siteConfig.url || '').replace(/\/$/, '');
      const seen = new Set();
      let count = 0;

      for await (const {htmlPath, route} of walkIndexFiles(outDir)) {
        if (route.startsWith('/404')) continue;

        const html = await fs.readFile(htmlPath, 'utf8');
        const title = extractTitle(html, route);
        const section = deriveSection(route);

        const slug = shortHash(`${route}::${title}`);
        const pngPath = path.join(ogDir, `${slug}.png`);
        const pngUrl = `${baseUrl}/img/og/${slug}.png`;

        if (!seen.has(slug)) {
          const svg = await satori(ogElement({title, section}), {
            width: W,
            height: H,
            fonts: [
              {name: 'Inter', data: fontRegular, weight: 400, style: 'normal'},
              {name: 'Inter', data: fontBold, weight: 700, style: 'normal'},
            ],
          });
          await sharp(Buffer.from(svg)).png({quality: 90}).toFile(pngPath);
          seen.add(slug);
        }

        const patched = patchOgMeta(html, pngUrl);
        if (patched !== html) {
          await fs.writeFile(htmlPath, patched);
        }
        count++;
      }

      console.log(
        `[og-images] generated ${seen.size} unique cards across ${count} pages`,
      );
    },
  };
};
