// xkcd_comic, Spectra img-body archetype (hero image + meta lockup).
// The default .img-hero/.img-meta rules from spectra-widgets.css are
// tuned for photos (album art, camera stills): object-fit: cover and
// a single-line, ellipsized .sub. A comic reads wrong cropped, and
// the whole point of this widget is a hovertext caption that's
// allowed to run more than one line, so both are overridden locally,
// scoped by the Shadow DOM boundary like every other widget's inline
// <style> block (see plugins/news_rss/client.js for the precedent).

function escapeHtml(s) {
  return String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[c]
  );
}

export default function render(shadow, ctx) {
  const data = ctx?.data ?? {};
  const opts = ctx?.cell?.options || {};
  const showTitle = opts.show_title !== false;
  const showHovertext = opts.show_hovertext !== false;
  const css = `<link rel="stylesheet" href="/static/style/spectra-widgets.css">`;

  if (data.error) {
    shadow.innerHTML = `
      ${css}
      <div class="w" data-widget="xkcd_comic">
        <div class="w-title"><i class="ph-bold ph-warning-circle"></i><h3>XKCD</h3></div>
        <div class="w-body"><p class="u-muted">${escapeHtml(data.error)}</p></div>
      </div>`;
    return;
  }

  if (!data.img) {
    shadow.innerHTML = `
      ${css}
      <div class="w" data-widget="xkcd_comic">
        <div class="w-title"><i class="ph-bold ph-image-square"></i><h3>XKCD</h3></div>
        <div class="w-body"><p class="u-muted">No comic to show.</p></div>
      </div>`;
    return;
  }

  const heading = showTitle && data.title ? data.title : "XKCD";
  const hovertext = showHovertext ? data.alt || "" : "";

  const layout = `
    .xkcd-hero img{
      object-fit: contain;
    }
    /* .img-meta .sub in spectra-widgets.css is a two-class compound
       selector (single-line, ellipsized, --fs-body); it outranks a
       bare .xkcd-hovertext rule on specificity regardless of source
       order, so every property that class sets has to be re-stated
       here under an equal-or-higher-specificity selector. */
    .img-meta .sub.xkcd-hovertext{
      white-space: normal;
      overflow: visible;
      text-overflow: clip;
      overflow-wrap: break-word;
      font-size: var(--fs-xs, 0.7em);
      line-height: var(--lh-snug, 1.3);
      font-style: italic;
    }
  `;

  shadow.innerHTML = `
    ${css}
    <style>${layout}</style>
    <div class="w" data-widget="xkcd_comic">
      <div class="w-title">
        <i class="ph-bold ph-image-square" style="color:var(--accent-4)"></i>
        <h3>${escapeHtml(heading)}</h3>
        ${data.num ? `<span class="w-title-meta">#${escapeHtml(String(data.num))}</span>` : ""}
      </div>
      <div class="w-body img-body">
        <div class="img-hero xkcd-hero"><img src="${escapeHtml(data.img)}" alt="${escapeHtml(data.alt)}"></div>
        ${hovertext ? `<div class="img-meta"><span class="sub xkcd-hovertext">${escapeHtml(hovertext)}</span></div>` : ""}
      </div>
    </div>`;
}
