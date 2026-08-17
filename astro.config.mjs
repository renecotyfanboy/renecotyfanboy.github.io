// @ts-check
import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeTableScroll from "./src/plugins/rehype-table-scroll.mjs";

// https://astro.build/config
export default defineConfig({
  // The repository's Pages settings serve the site from this custom domain;
  // renecotyfanboy.github.io only 301s here. Getting this wrong points every
  // canonical, og:url, sitemap entry and RSS link at the redirecting host.
  site: "https://sdupourque.me",

  integrations: [sitemap()],

  markdown: {
    remarkPlugins: [remarkMath],
    rehypePlugins: [rehypeKatex, rehypeTableScroll],
    shikiConfig: {
      // Dark, warm-accented — the closest bundled theme to the site palette.
      theme: "vesper",
      wrap: false,
    },
  },

  build: {
    // Stable asset directory: notebook output lands next to its markdown, so
    // keeping the name fixed makes generated diffs easier to read.
    assets: "_assets",
  },
});
