import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const posts = defineCollection({
  loader: glob({ base: "./src/content/posts", pattern: "**/*.md" }),
  schema: z.object({
    title: z.string(),
    description: z.string().optional(),
    date: z.coerce.date(),
    tags: z.array(z.string()).default([]),
    draft: z.boolean().default(false),

    /* `notebook` posts are generated from notebooks/ by the jupytext +
       nbconvert pipeline, and get a provenance banner linking back to the
       executable source. */
    source: z.enum(["prose", "notebook"]).default("prose"),
    notebook: z.string().optional(), // path in the repo, e.g. notebooks/foo.md

    /* Written by scripts/build_notebooks.py. It is what lets that script tell
       its own output apart from hand-written posts, so it can delete entries
       whose source notebook was renamed or removed. Never set by hand. */
    generated: z.boolean().default(false),
  }),
});

export const collections = { posts };
