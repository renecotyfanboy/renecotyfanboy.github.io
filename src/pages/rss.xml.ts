import rss from "@astrojs/rss";
import type { APIContext } from "astro";
import { getPosts } from "../utils/posts";
import { SITE } from "../consts";

export async function GET(context: APIContext) {
  const posts = await getPosts();

  return rss({
    title: SITE.title,
    description: SITE.description,
    site: context.site!,
    items: posts.map((post) => ({
      title: post.data.title,
      description: post.data.description ?? "",
      pubDate: post.data.date,
      categories: post.data.tags,
      link: `/blog/${post.id}/`,
    })),
    customData: `<language>${SITE.locale}</language>`,
  });
}
