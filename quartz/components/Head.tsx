import { i18n } from "../i18n"
import { FullSlug, getFileExtension, joinSegments, pathToRoot } from "../util/path"
import { CSSResourceToStyleElement, JSResourceToScriptElement } from "../util/resources"
import { googleFontHref, googleFontSubsetHref } from "../util/theme"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import { unescapeHTML } from "../util/escape"

function jsonLd(fileData: QuartzComponentProps["fileData"], baseUrl?: string) {
  const frontmatter = (fileData.frontmatter ?? {}) as Record<string, unknown>
  const schemaType = (frontmatter.schema_type as string | undefined) ?? "DigitalDocument"
  const canonicalBase = `https://${baseUrl ?? "mvattulainen.github.io/ichgcpe6r3fin"}`.replace(/\/$/, "")
  const permalink = (frontmatter.permalink as string | undefined) ?? `/${fileData.slug ?? ""}/`
  const pageUrl = `${canonicalBase}${permalink.startsWith("/") ? "" : "/"}${permalink}`
  return {
    "@context": "https://schema.org",
    "@type": schemaType,
    "@id": `${pageUrl.replace(/\/$/, "")}/#page`,
    identifier: frontmatter.id,
    name: frontmatter.title,
    headline: frontmatter.title,
    inLanguage: (frontmatter.language as string | undefined) ?? "fi",
    url: pageUrl,
    isPartOf: { "@id": `${canonicalBase}/ich-e6-r3/#guideline` },
    translationOfWork:
      frontmatter.translation_status === "unofficial"
        ? {
            "@type": "DigitalDocument",
            name: "ICH E6(R3) Guideline for Good Clinical Practice",
            inLanguage: "en",
          }
        : undefined,
    isBasedOn: frontmatter.is_based_on
      ? [
          {
            "@type": "DigitalDocument",
            identifier: "ich-e6-r3-fi-v1",
            name: "Fimean tarkistama epävirallinen suomenkielinen käännös",
            inLanguage: "fi",
          },
          {
            "@type": "DigitalDocument",
            identifier: "ich-e6-r3-en-step5",
            name: "ICH E6(R3) Step 5",
            inLanguage: "en",
          },
        ]
      : undefined,
    version: frontmatter.document_id === "ich-e6-r3-fi-v1" ? "1" : undefined,
    articleSection: frontmatter.section_number,
    sdPublisher: {
      "@type": "Organization",
      name: "ICH E6(R3) suomenkielinen tietopohja",
    },
    sdDatePublished: "2026-07-17",
  }
}
export default (() => {
  const Head: QuartzComponent = ({ cfg, fileData, externalResources }: QuartzComponentProps) => {
    const titleSuffix = cfg.pageTitleSuffix ?? ""
    const title =
      (fileData.frontmatter?.title ?? i18n(cfg.locale).propertyDefaults.title) + titleSuffix
    const description =
      fileData.frontmatter?.socialDescription ??
      fileData.frontmatter?.description ??
      unescapeHTML(fileData.description?.trim() ?? i18n(cfg.locale).propertyDefaults.description)

    const { css, js, additionalHead } = externalResources

    const url = new URL(`https://${cfg.baseUrl ?? "example.com"}`)
    const path = url.pathname as FullSlug
    const baseDir = fileData.slug === "404" ? path : pathToRoot(fileData.slug!)
    const iconPath = joinSegments(baseDir, "static/icon.png")

    // Url of current page
    const socialUrl =
      fileData.slug === "404" ? url.toString() : joinSegments(url.toString(), fileData.slug!)

    const usesCustomOgImage = false
    const ogImageDefaultPath = `https://${cfg.baseUrl}/static/og-image.png`

    const coreStylesheet = css[0]?.content
    const coreScript = js.find(
      (r) => r.loadTime === "beforeDOMReady" && r.contentType === "external",
    )

    return (
      <head>
        <title>{title}</title>
        <meta charSet="utf-8" />
        {coreStylesheet && <link rel="preload" href={coreStylesheet} as="style" />}
        {coreScript && coreScript.contentType === "external" && (
          <link rel="preload" href={coreScript.src} as="script" />
        )}
        {cfg.theme.cdnCaching && cfg.theme.fontOrigin === "googleFonts" && (
          <>
            <link rel="preconnect" href="https://fonts.googleapis.com" />
            <link rel="preconnect" href="https://fonts.gstatic.com" />
            <link rel="stylesheet" href={googleFontHref(cfg.theme)} />
            {cfg.theme.typography.title && (
              <link rel="stylesheet" href={googleFontSubsetHref(cfg.theme, cfg.pageTitle)} />
            )}
          </>
        )}
        <link rel="preconnect" href="https://cdnjs.cloudflare.com" crossOrigin="anonymous" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />

        <meta name="og:site_name" content={cfg.pageTitle}></meta>
        <meta property="og:title" content={title} />
        <meta property="og:type" content="website" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={title} />
        <meta name="twitter:description" content={description} />
        <meta property="og:description" content={description} />
        <meta property="og:image:alt" content={description} />

        {!usesCustomOgImage && (
          <>
            <meta property="og:image" content={ogImageDefaultPath} />
            <meta property="og:image:url" content={ogImageDefaultPath} />
            <meta name="twitter:image" content={ogImageDefaultPath} />
            <meta
              property="og:image:type"
              content={`image/${getFileExtension(ogImageDefaultPath) ?? "png"}`}
            />
          </>
        )}

        {cfg.baseUrl && (
          <>
            <meta property="twitter:domain" content={cfg.baseUrl}></meta>
            <meta property="og:url" content={socialUrl}></meta>
            <meta property="twitter:url" content={socialUrl}></meta>
          </>
        )}

        <link rel="icon" href={iconPath} />
        <meta name="description" content={description} />
        <meta name="generator" content="Quartz" />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd(fileData, cfg.baseUrl)) }}
        />

        {css.map((resource) => CSSResourceToStyleElement(resource, true))}
        {js
          .filter((resource) => resource.loadTime === "beforeDOMReady")
          .map((res) => JSResourceToScriptElement(res, true))}
        {additionalHead.map((resource) => {
          if (typeof resource === "function") {
            return resource(fileData)
          } else {
            return resource
          }
        })}
      </head>
    )
  }

  return Head
}) satisfies QuartzComponentConstructor
