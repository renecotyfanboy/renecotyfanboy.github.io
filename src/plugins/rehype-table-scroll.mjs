/**
 * Wrap every markdown `<table>` in `<div class="table-scroll">`.
 *
 * Markdown has no syntax for a wrapper element, so a table wide enough to
 * exceed its grid column would otherwise push the whole page into horizontal
 * scroll. One long unbreakable token in a DataFrame cell is enough to trigger
 * it. The wrapper is what `.table-scroll { overflow-x: auto }` needs to bite.
 *
 * Written by hand rather than with unist-util-visit: the traversal is six
 * lines and this keeps the dependency out of the build.
 */
export default function rehypeTableScroll() {
  return (tree) => {
    const walk = (node) => {
      if (!Array.isArray(node.children)) return;

      node.children = node.children.map((child) => {
        walk(child);

        if (child.type !== "element" || child.tagName !== "table") return child;

        return {
          type: "element",
          tagName: "div",
          properties: { className: ["table-scroll"] },
          children: [child],
        };
      });
    };

    walk(tree);
  };
}
