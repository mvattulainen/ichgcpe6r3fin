import YAML from "yaml"
import { QuartzTransformerPlugin } from "../types"

export const Frontmatter: QuartzTransformerPlugin = () => ({
  name: "Frontmatter",
  markdownPlugins() {
    return [
      () => (tree: any, file: any) => {
        const source = String(file.value ?? "")
        const match = source.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/)
        if (!match) return

        const parsed = YAML.parse(match[1]) ?? {}
        if (typeof parsed !== "object" || Array.isArray(parsed)) return
        file.data.frontmatter = parsed

        const endOffset = match[0].length
        tree.children = tree.children.filter((node: any) => {
          const end = node.position?.end?.offset
          return typeof end !== "number" || end > endOffset
        })
      },
    ]
  },
})
