import type {
  QuartzComponent,
  QuartzComponentConstructor,
  QuartzComponentProps,
} from "@quartz-community/types"
import { htmlToJsx } from "@quartz-community/utils/jsx"
import type { Root } from "hast"

interface FolderContentOptions {
  showFolderCount?: boolean
  showSubfolders?: boolean
}

/**
 * Render only the authored index.md content.
 *
 * The upstream folder-page component appends an automatically generated item
 * count and object list. This knowledge base already has curated folder index
 * links, so the automatic listing is intentionally omitted.
 */
export default ((options?: Partial<FolderContentOptions>) => {
  void options

  const FolderContent: QuartzComponent = ({ tree, fileData }: QuartzComponentProps) => {
    const cssClasses =
      ((fileData as { frontmatter?: { cssclasses?: string[] } } | undefined)?.frontmatter
        ?.cssclasses as string[] | undefined) ?? []
    const content =
      (tree as Root).children.length === 0
        ? (fileData as { description?: unknown } | undefined)?.description
        : htmlToJsx(tree as Root)

    return (
      <div class="popover-hint">
        <article class={cssClasses.join(" ")}>
          <div class="markdown-preview-view markdown-rendered">{content}</div>
        </article>
      </div>
    )
  }

  return FolderContent
}) satisfies QuartzComponentConstructor
