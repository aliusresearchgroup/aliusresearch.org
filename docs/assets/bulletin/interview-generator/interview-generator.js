(function () {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const encoder = new TextEncoder();

  function setStatus(message) {
    const status = $("#generator-status");
    if (status) status.textContent = message;
  }

  function valueOf(name) {
    const node = document.querySelector(`[name="${name}"]`);
    return node ? node.value.trim() : "";
  }

  function slugify(value) {
    const slug = value
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
    return slug || "generated-interview";
  }

  function texEscape(value) {
    return String(value || "")
      .replace(/\\/g, "\\textbackslash{}")
      .replace(/&/g, "\\&")
      .replace(/%/g, "\\%")
      .replace(/\$/g, "\\$")
      .replace(/#/g, "\\#")
      .replace(/_/g, "\\_")
      .replace(/\{/g, "\\{")
      .replace(/\}/g, "\\}")
      .replace(/~/g, "\\textasciitilde{}")
      .replace(/\^/g, "\\textasciicircum{}")
      .replace(/\n+/g, " ");
  }

  function texTitle(value) {
    return texEscape(value).replace(/\s*\/\s*/g, " / ");
  }

  function htmlEscape(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function stripOuterQuotationMarks(value) {
    let text = String(value || "").trim();
    const pairs = [
      ['"', '"'],
      ["'", "'"],
      ["\u201c", "\u201d"],
      ["\u2018", "\u2019"],
      ["\u00ab", "\u00bb"]
    ];

    let changed = true;
    while (changed && text.length > 1) {
      changed = false;
      pairs.forEach(([open, close]) => {
        if (text.startsWith(open) && text.endsWith(close)) {
          text = text.slice(open.length, -close.length).trim();
          changed = true;
        }
      });
    }
    return text;
  }

  function previewQuote(value) {
    return `&ldquo;${htmlEscape(stripOuterQuotationMarks(value))}&rdquo;`;
  }

  function paragraphs(value) {
    return String(value || "")
      .split(/\n{2,}/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function lines(value) {
    return String(value || "")
      .split(/\n+/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function collectQuestions() {
    return $$(".qa-item").map((item) => ({
      question: $(".qa-question", item).value.trim(),
      answer: $(".qa-answer", item).value.trim(),
      quote: $(".qa-quote", item).value.trim()
    })).filter((item) => item.question || item.answer || item.quote);
  }

  function collectData() {
    const title = valueOf("title") || "Generated ALIUS interview";
    const interviewee = valueOf("intervieweeName") || "Interviewee Name";
    const interviewer = valueOf("interviewerName") || "Interviewer Name";
    const slug = slugify(valueOf("slug") || `${interviewee}-${title}`);
    const citation = valueOf("citation") || `${interviewee} & ${interviewer} (${valueOf("year") || "2026"}). ${title}. ALIUS Bulletin.`;
    return {
      slug,
      issueNumber: valueOf("issueNumber") || "future",
      year: valueOf("year") || "2026",
      issueDate: valueOf("issueDate"),
      editors: valueOf("editors"),
      title,
      subtitle: valueOf("subtitle") || `An interview with ${interviewee}`,
      interviewee,
      intervieweeCredentials: valueOf("intervieweeCredentials"),
      interviewer,
      interviewerCredentials: valueOf("interviewerCredentials"),
      creditLine: valueOf("creditLine") || `By ${interviewer}`,
      citation,
      doi: valueOf("doi"),
      abstract: valueOf("abstract"),
      keywords: valueOf("keywords"),
      references: valueOf("references"),
      questions: collectQuestions()
    };
  }

  function contributorMacro(name, credentials) {
    const detail = lines(credentials).map(texEscape).join("\\\\");
    return `\\AliusContributor{${texEscape(name)}}{${detail}}`;
  }

  function generatedInterviewTex(data) {
    const chunks = [];
    data.questions.forEach((item) => {
      if (item.question) chunks.push(`\\AliusQuestion{${texEscape(item.question)}}`);
      paragraphs(item.answer).forEach((paragraph) => {
        chunks.push(`\\AliusParagraph{${texEscape(paragraph)}}`);
      });
      if (item.quote) chunks.push(`\\AliusPullQuote{${texEscape(stripOuterQuotationMarks(item.quote))}}`);
      chunks.push("");
    });
    const referenceLines = lines(data.references);
    if (referenceLines.length) {
      chunks.push("\\AliusSectionHeading{References}");
      referenceLines.forEach((line) => chunks.push(`\\AliusReferenceEntry{${texEscape(line)}}`));
      chunks.push("");
    }
    return chunks.join("\n");
  }

  function generatedMainTex(data) {
    const contributorOne = contributorMacro(data.interviewee, data.intervieweeCredentials);
    const contributorTwo = contributorMacro(data.interviewer, data.interviewerCredentials);
    const doiLine = data.doi ? `\\AliusMetaLine{DOI/URL}{${texEscape(data.doi)}}` : "";
    return [
      "% !TEX TS-program = lualatex",
      "% Self-contained ALIUS Bulletin interview generated by aliusresearch.org.",
      "% Upload this file and references.bib to Overleaf and compile with LuaLaTeX.",
      "\\documentclass[11pt,a4paper]{article}",
      "\\usepackage[a4paper,top=24mm,bottom=22mm,left=30mm,right=30mm]{geometry}",
      "\\usepackage{xcolor}",
      "\\usepackage{fontspec}",
      "\\usepackage{microtype}",
      "\\usepackage{ragged2e}",
      "\\usepackage{hyperref}",
      "\\usepackage{fancyhdr}",
      "\\usepackage{etoolbox}",
      "\\definecolor{AliusQuestionGreen}{HTML}{1F8135}",
      "\\definecolor{AliusTextBlack}{HTML}{000000}",
      "\\definecolor{AliusQuoteGray}{HTML}{595959}",
      "\\definecolor{AliusFooterGray}{HTML}{767171}",
      "\\definecolor{AliusRule}{HTML}{D9E3DA}",
      "\\IfFontExistsTF{Lato}{\\newfontfamily\\AliusSans{Lato}}{\\newfontfamily\\AliusSans{Latin Modern Sans}}",
      "\\IfFontExistsTF{Lato Light}{\\newfontfamily\\AliusSansLight{Lato Light}}{\\newfontfamily\\AliusSansLight{Latin Modern Sans}}",
      "\\IfFontExistsTF{Cormorant Garamond}{\\newfontfamily\\AliusSerif{Cormorant Garamond}}{\\newfontfamily\\AliusSerif{TeX Gyre Pagella}}",
      "\\IfFontExistsTF{Cormorant Garamond Light}{\\newfontfamily\\AliusSerifLight{Cormorant Garamond Light}}{\\newfontfamily\\AliusSerifLight{TeX Gyre Pagella}}",
      "\\IfFontExistsTF{Georgia}{\\newfontfamily\\AliusQuoteFont{Georgia}}{\\newfontfamily\\AliusQuoteFont{TeX Gyre Pagella}}",
      "\\setmainfont{TeX Gyre Pagella}",
      "\\hypersetup{colorlinks=true,urlcolor=AliusQuestionGreen,linkcolor=AliusQuestionGreen}",
      "\\pagestyle{fancy}",
      "\\fancyhf{}",
      `\\fancyhead[L]{{\\AliusSans\\fontsize{8.5}{10}\\selectfont ALIUS Bulletin ${texEscape(data.issueNumber)} -- ${texEscape(data.year)}}}`,
      `\\fancyhead[R]{{\\AliusSans\\fontsize{8.5}{10}\\selectfont ${texEscape(data.interviewee)}}}`,
      "\\fancyfoot[C]{\\AliusSans\\fontsize{8}{10}\\selectfont\\textcolor{AliusFooterGray}{\\thepage}}",
      "\\renewcommand{\\headrulewidth}{0pt}",
      "\\renewcommand{\\footrulewidth}{0pt}",
      "\\setlength{\\headheight}{14pt}",
      "\\setlength{\\parindent}{0pt}",
      "\\setlength{\\parskip}{0pt}",
      "\\newcommand{\\AliusTitle}[1]{\\begin{center}{\\AliusSansLight\\fontsize{24}{28}\\selectfont #1\\par}\\end{center}\\vspace{2mm}}",
      "\\newcommand{\\AliusSubtitle}[1]{\\begin{center}{\\AliusSans\\fontsize{14}{18}\\selectfont #1\\par}\\end{center}\\vspace{1mm}}",
      "\\newcommand{\\AliusCredit}[1]{\\begin{center}{\\AliusSans\\fontsize{14}{17}\\selectfont #1\\par}\\end{center}\\vspace{7mm}}",
      "\\newcommand{\\AliusMetaLine}[2]{{\\AliusSerif\\fontsize{11.5}{15}\\selectfont\\textcolor{AliusQuestionGreen}{#1:} #2\\par\\vspace{1.5mm}}}",
      "\\newcommand{\\AliusContributor}[2]{\\begin{minipage}[t]{0.46\\linewidth}{\\AliusSans\\fontsize{10}{12}\\selectfont\\textcolor{AliusQuestionGreen}{#1}\\par}{\\AliusSerif\\fontsize{10}{12}\\selectfont #2\\par}\\end{minipage}}",
      "\\newcommand{\\AliusQuestion}[1]{\\vspace{4mm}{\\AliusSans\\fontsize{12.5}{17.2}\\selectfont\\textcolor{AliusQuestionGreen}{#1}\\par}\\vspace{1.5mm}}",
      "\\newcommand{\\AliusParagraph}[1]{{\\AliusSerif\\fontsize{14}{19.5}\\selectfont\\justifying\\textcolor{AliusTextBlack}{#1}\\par}\\vspace{2.2mm}}",
      "\\newcommand{\\AliusPullQuote}[1]{\\vspace{4mm}\\begin{center}\\begin{minipage}{0.78\\linewidth}\\centering{\\AliusQuoteFont\\itshape\\fontsize{18}{22}\\selectfont\\textcolor{AliusQuoteGray}{``#1''}\\par}\\end{minipage}\\end{center}\\vspace{4mm}}",
      "\\newcommand{\\AliusSectionHeading}[1]{\\vspace{5mm}{\\AliusSans\\fontsize{15}{18}\\selectfont #1\\par}\\vspace{2mm}}",
      "\\newcommand{\\AliusReferenceEntry}[1]{{\\AliusSerif\\fontsize{11.5}{14}\\selectfont #1\\par}}",
      "\\begin{document}",
      `\\AliusTitle{${texTitle(data.title)}}`,
      `\\AliusSubtitle{${texEscape(data.subtitle)}}`,
      `\\AliusCredit{${texEscape(data.creditLine)}}`,
      "\\vspace{1mm}{\\color{AliusRule}\\hrule height 0.4pt}\\vspace{4mm}",
      `\\AliusMetaLine{Cite as}{${texEscape(data.citation)}}`,
      doiLine,
      `\\AliusMetaLine{Abstract}{${texEscape(data.abstract)}}`,
      `\\AliusMetaLine{Keywords}{${texEscape(data.keywords)}}`,
      "\\vspace{3mm}",
      "\\noindent" + contributorOne + "\\hfill" + contributorTwo,
      "\\vspace{8mm}",
      generatedInterviewTex(data),
      "\\end{document}",
      ""
    ].filter((line) => line !== "").join("\n");
  }

  function bibEscape(value) {
    return String(value || "").replace(/[{}]/g, "").replace(/\n+/g, " ");
  }

  function generatedBib(data) {
    const plainReferences = lines(data.references);
    const comments = plainReferences.length
      ? ["", "% Plain-text references entered in the GUI:", ...plainReferences.map((line) => `% ${line}`)]
      : [];
    return [
      `@misc{${data.slug},`,
      `  author = {${bibEscape(data.interviewee)} and ${bibEscape(data.interviewer)}},`,
      `  title = {${bibEscape(data.title)}},`,
      `  year = {${bibEscape(data.year)}},`,
      "  howpublished = {ALIUS Bulletin},",
      `  note = {${bibEscape(data.doi || data.citation)}}`,
      "}",
      ...comments,
      ""
    ].join("\n");
  }

  function crc32(bytes) {
    let crc = -1;
    for (let index = 0; index < bytes.length; index += 1) {
      crc = (crc >>> 8) ^ crcTable[(crc ^ bytes[index]) & 0xff];
    }
    return (crc ^ -1) >>> 0;
  }

  const crcTable = (() => {
    const table = new Uint32Array(256);
    for (let index = 0; index < 256; index += 1) {
      let value = index;
      for (let bit = 0; bit < 8; bit += 1) {
        value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
      }
      table[index] = value >>> 0;
    }
    return table;
  })();

  function uint16(value) {
    return [value & 0xff, (value >>> 8) & 0xff];
  }

  function uint32(value) {
    return [value & 0xff, (value >>> 8) & 0xff, (value >>> 16) & 0xff, (value >>> 24) & 0xff];
  }

  function bytesFrom(parts) {
    const size = parts.reduce((total, part) => total + part.length, 0);
    const out = new Uint8Array(size);
    let offset = 0;
    parts.forEach((part) => {
      out.set(part, offset);
      offset += part.length;
    });
    return out;
  }

  function makeZip(files) {
    const localParts = [];
    const centralParts = [];
    let offset = 0;

    files.forEach((file) => {
      const nameBytes = encoder.encode(file.path.replace(/\\/g, "/"));
      const dataBytes = typeof file.content === "string" ? encoder.encode(file.content) : file.content;
      const checksum = crc32(dataBytes);
      const localHeader = bytesFrom([
        new Uint8Array(uint32(0x04034b50)),
        new Uint8Array(uint16(20)),
        new Uint8Array(uint16(0x0800)),
        new Uint8Array(uint16(0)),
        new Uint8Array(uint16(0)),
        new Uint8Array(uint16(0)),
        new Uint8Array(uint32(checksum)),
        new Uint8Array(uint32(dataBytes.length)),
        new Uint8Array(uint32(dataBytes.length)),
        new Uint8Array(uint16(nameBytes.length)),
        new Uint8Array(uint16(0)),
        nameBytes,
        dataBytes
      ]);
      localParts.push(localHeader);

      const centralHeader = bytesFrom([
        new Uint8Array(uint32(0x02014b50)),
        new Uint8Array(uint16(20)),
        new Uint8Array(uint16(20)),
        new Uint8Array(uint16(0x0800)),
        new Uint8Array(uint16(0)),
        new Uint8Array(uint16(0)),
        new Uint8Array(uint16(0)),
        new Uint8Array(uint32(checksum)),
        new Uint8Array(uint32(dataBytes.length)),
        new Uint8Array(uint32(dataBytes.length)),
        new Uint8Array(uint16(nameBytes.length)),
        new Uint8Array(uint16(0)),
        new Uint8Array(uint16(0)),
        new Uint8Array(uint16(0)),
        new Uint8Array(uint16(0)),
        new Uint8Array(uint32(0)),
        new Uint8Array(uint32(offset)),
        nameBytes
      ]);
      centralParts.push(centralHeader);
      offset += localHeader.length;
    });

    const centralSize = centralParts.reduce((total, part) => total + part.length, 0);
    const end = bytesFrom([
      new Uint8Array(uint32(0x06054b50)),
      new Uint8Array(uint16(0)),
      new Uint8Array(uint16(0)),
      new Uint8Array(uint16(files.length)),
      new Uint8Array(uint16(files.length)),
      new Uint8Array(uint32(centralSize)),
      new Uint8Array(uint32(offset)),
      new Uint8Array(uint16(0))
    ]);
    return new Blob([...localParts, ...centralParts, end], { type: "application/zip" });
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 500);
  }

  async function downloadOverleafZip() {
    const data = collectData();
    setStatus("Building Overleaf ZIP...");
    const files = [
      { path: "main.tex", content: generatedMainTex(data) },
      { path: "references.bib", content: generatedBib(data) }
    ];

    const zip = makeZip(files);
    downloadBlob(zip, `alius-interview-${data.slug}.zip`);
    setStatus("Overleaf ZIP ready.");
  }

  function previewContributorHtml(name, credentials) {
    const detail = lines(credentials)
      .map((line) => `<p>${htmlEscape(line)}</p>`)
      .join("");
    return `
      <div class="alius-print-contributor">
        <strong>${htmlEscape(name)}</strong>
        ${detail}
      </div>
    `;
  }

  function previewHtml(data) {
    const qas = data.questions.map((item) => {
      const answer = paragraphs(item.answer)
        .map((paragraph) => `<p class="alius-print-answer">${htmlEscape(paragraph)}</p>`)
        .join("");
      const quote = item.quote ? `<blockquote class="alius-print-quote">${previewQuote(item.quote)}</blockquote>` : "";
      return [
        item.question ? `<p class="alius-print-question">${htmlEscape(item.question)}</p>` : "",
        answer,
        quote
      ].join("");
    }).join("");
    const abstract = data.abstract
      ? `<section class="alius-print-abstract-block"><h3>Abstract</h3>${paragraphs(data.abstract).map((paragraph) => `<p class="alius-print-abstract">${htmlEscape(paragraph)}</p>`).join("")}</section>`
      : "";
    const keywords = data.keywords
      ? `<p class="alius-print-keywords"><strong>Keywords:</strong> ${htmlEscape(data.keywords)}</p>`
      : "";
    const references = lines(data.references).length
      ? `<h3 class="alius-print-section">References</h3>${lines(data.references).map((line) => `<p class="alius-print-answer">${htmlEscape(line)}</p>`).join("")}`
      : "";
    return `
      <article class="alius-print-page">
        <h2 class="alius-print-title">${htmlEscape(data.title)}</h2>
        <div class="alius-print-front">
          <div class="alius-print-front-left">
            <p class="alius-print-subtitle">${htmlEscape(data.subtitle)}</p>
            <p class="alius-print-interviewee">${htmlEscape(data.interviewee)}</p>
            <p class="alius-print-credit">${htmlEscape(data.creditLine)}</p>
            <p class="alius-print-citation"><strong>Citation:</strong> ${htmlEscape(data.citation)}</p>
          </div>
          <div class="alius-print-contributors">
            ${previewContributorHtml(data.interviewee, data.intervieweeCredentials)}
            ${previewContributorHtml(data.interviewer, data.interviewerCredentials)}
          </div>
        </div>
        ${abstract}
        ${keywords}
        ${qas}
        ${references}
        <footer class="alius-print-footer">
          <span>ALIUS Bulletin n&deg;${htmlEscape(data.issueNumber)} (${htmlEscape(data.year)})</span>
          <span>aliusresearch.org/bulletin</span>
        </footer>
      </article>
    `;
  }

  function refreshPreview() {
    const preview = $("#interview-preview");
    if (preview) preview.innerHTML = previewHtml(collectData());
  }

  function addQuestion(seed) {
    const list = $("#qa-list");
    const item = document.createElement("div");
    item.className = "qa-item";
    item.innerHTML = `
      <div class="qa-item__bar">
        <strong>Question ${list.children.length + 1}</strong>
        <button class="generator-button danger qa-remove" type="button">Remove</button>
      </div>
      <div class="field-grid">
        <div class="generator-field span-2">
          <label>Question</label>
          <textarea class="qa-question">${htmlEscape(seed && seed.question || "")}</textarea>
        </div>
        <div class="generator-field span-2">
          <label>Answer</label>
          <textarea class="qa-answer">${htmlEscape(seed && seed.answer || "")}</textarea>
        </div>
        <div class="generator-field span-2">
          <label>Most notable quote from this answer</label>
          <textarea class="qa-quote">${htmlEscape(seed && seed.quote || "")}</textarea>
        </div>
      </div>
    `;
    $(".qa-remove", item).addEventListener("click", () => {
      item.remove();
      renumberQuestions();
      refreshPreview();
    });
    ["input", "change"].forEach((eventName) => {
      item.addEventListener(eventName, refreshPreview);
    });
    list.appendChild(item);
    renumberQuestions();
    refreshPreview();
  }

  function renumberQuestions() {
    $$(".qa-item").forEach((item, index) => {
      const title = $(".qa-item__bar strong", item);
      if (title) title.textContent = `Question ${index + 1}`;
    });
  }

  function bindEvents() {
    $("#add-question").addEventListener("click", () => addQuestion());
    $("#download-zip").addEventListener("click", () => {
      downloadOverleafZip().catch((error) => {
        console.error(error);
        setStatus(error.message || "Could not build the ZIP.");
      });
    });
    $("#print-pdf").addEventListener("click", () => {
      refreshPreview();
      setStatus("Use the browser print dialog to save as PDF.");
      window.print();
    });
    document.addEventListener("input", (event) => {
      if (event.target.closest("#interview-generator-form")) refreshPreview();
    });
  }

  function init() {
    addQuestion({
      question: "What question opens the conversation?",
      answer: "Write the interviewee answer here. Separate paragraphs with a blank line.",
      quote: "Place a short notable quotation here."
    });
    bindEvents();
    refreshPreview();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
