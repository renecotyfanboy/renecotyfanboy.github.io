export const SITE = {
  title: "An astrophysicist doing stuff",
  tagline: "An astrophysicist doing stuff",
  description:
    "Personal website of Simon Dupourqué — astrophysicist working on Bayesian inference and numerical methods for X-ray astronomy.",
  author: "Simon Dupourqué",
  email: "simon.dupourque@utoulouse.fr",
  locale: "en",
} as const;

export const NAV = [
  { label: "Blog", href: "/blog" },
  { label: "Academia", href: "/academia" },
  { label: "CV", href: "/cv" },
] as const;

export const SOCIALS = [
  { label: "GitHub", href: "https://github.com/renecotyfanboy", icon: "github" },
  { label: "ORCID", href: "https://orcid.org/0000-0003-2715-8986", icon: "orcid" },
  { label: "Email", href: `mailto:${SITE.email}`, icon: "mail" },
  { label: "RSS", href: "/rss.xml", icon: "rss" },
] as const;

/* Deliberately the author query rather than an `orcid:` one: the ORCID search
   only returns papers claimed there and misses several, so it would show fewer
   entries than the page lists. This mirrors the query in
   scripts/fetch_publications.py, so the link and the list agree. */
export const SCIX_SEARCH =
  'https://scixplorer.org/search?q=author%3A%22Dupourqu%C3%A9%2C%20S.%22&sort=date%20desc';
