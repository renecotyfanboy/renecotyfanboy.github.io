import { getCollection, type CollectionEntry } from "astro:content";

export type Post = CollectionEntry<"posts">;

export type Tag = { tag: string; slug: string; count: number };

/**
 * URL-safe form of a tag. Tags are authored as free text in front matter, so
 * a natural one like "machine learning" would otherwise become a route with a
 * space in it — and a link that no longer matches the generated path.
 */
export function tagSlug(tag: string): string {
  return tag
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "") // strip diacritics
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

/** Newest first. Drafts are hidden in production builds only. */
export async function getPosts(): Promise<Post[]> {
  const posts = await getCollection("posts", ({ data }) =>
    import.meta.env.PROD ? !data.draft : true,
  );
  return posts.sort((a, b) => b.data.date.getTime() - a.data.date.getTime());
}

export async function getTags(): Promise<Tag[]> {
  const posts = await getPosts();
  const counts = new Map<string, Tag>();

  for (const p of posts) {
    for (const tag of p.data.tags) {
      const slug = tagSlug(tag);
      const seen = counts.get(slug);
      if (seen) seen.count += 1;
      else counts.set(slug, { tag, slug, count: 1 });
    }
  }

  return [...counts.values()].sort(
    (a, b) => b.count - a.count || a.tag.localeCompare(b.tag),
  );
}
