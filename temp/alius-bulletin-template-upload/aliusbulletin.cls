\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{aliusbulletin}[2026/04/22 ALIUS Bulletin reconstruction template]

\LoadClass[11pt]{article}

\RequirePackage[a4paper,left=31.75mm,right=31.75mm,top=25.40mm,bottom=28.50mm,headheight=34pt,headsep=10pt,footskip=18pt]{geometry}
\RequirePackage[english]{babel}
\RequirePackage{calc}
\RequirePackage{etoolbox}
\RequirePackage{fancyhdr}
\RequirePackage{fontspec}
\RequirePackage{graphicx}
\RequirePackage{xcolor}
\RequirePackage{hyperref}
\RequirePackage{lipsum}
\RequirePackage{microtype}
\RequirePackage{ragged2e}
\RequirePackage{setspace}
\RequirePackage{tikz}
\RequirePackage{xparse}
\usetikzlibrary{calc}

\hypersetup{
  colorlinks=true,
  linkcolor=black,
  urlcolor=black,
  citecolor=black,
  pdfauthor={ALIUS},
  pdftitle={ALIUS Bulletin}
}

\defaultfontfeatures{Ligatures=TeX,Scale=MatchLowercase}
\setmainfont[
  Path=assets/fonts/,
  UprightFont=CormorantGaramond-Regular.ttf,
  ItalicFont=CormorantGaramond-Italic.ttf,
  BoldFont=CormorantGaramond-Bold.ttf,
  BoldItalicFont=CormorantGaramond-BoldItalic.ttf
]{Cormorant Garamond}

\newfontfamily\AliusLato[
  Path=assets/fonts/,
  UprightFont=Lato-Regular.ttf,
  ItalicFont=Lato-Italic.ttf,
  BoldFont=Lato-Bold.ttf,
  BoldItalicFont=Lato-BoldItalic.ttf
]{Lato}

\newfontfamily\AliusLatoLight[
  Path=assets/fonts/,
  UprightFont=Lato-Light.ttf,
  ItalicFont=Lato-LightItalic.ttf,
  BoldFont=Lato-Regular.ttf,
  BoldItalicFont=Lato-Italic.ttf
]{Lato}

\newfontfamily\AliusCormorantLight[
  Path=assets/fonts/,
  UprightFont=CormorantGaramond-Light.ttf,
  ItalicFont=CormorantGaramond-LightItalic.ttf,
  BoldFont=CormorantGaramond-Regular.ttf,
  BoldItalicFont=CormorantGaramond-Italic.ttf
]{Cormorant Garamond}

\microtypesetup{protrusion=true,expansion=true}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
\raggedbottom

\definecolor{AliusGreen}{HTML}{83BC25}
\definecolor{AliusGreenDark}{HTML}{068236}
\definecolor{AliusCoverInk}{HTML}{111111}
\definecolor{AliusCoverPanel}{HTML}{000000}
\definecolor{AliusBody}{HTML}{515151}
\color{AliusBody}

\makeatletter

\newif\ifAliusBundleMode
\AliusBundleModefalse

\def\AliusIssueNumber{}
\def\AliusYear{}
\def\AliusPieceSlug{}
\def\AliusPieceType{}
\def\AliusTitle{}
\def\AliusSubtitle{}
\def\AliusCreditLine{}
\def\AliusRunningTitle{}
\def\AliusCitationLabel{Cite as:}
\def\AliusStandaloneCitation{}
\def\AliusBundleCitation{}
\def\AliusAbstract{}
\def\AliusKeywordsLabel{Keywords:}
\def\AliusKeywords{}
\def\AliusContributors{}
\def\AliusTitleSize{20}
\def\AliusTitleLeading{24}
\def\AliusSubtitleSize{20}
\def\AliusSubtitleLeading{24}
\def\AliusCreditSize{13}
\def\AliusCreditLeading{15}
\def\AliusFooterPrefix{ALIUS Bulletin}
\def\AliusFooterUrl{aliusresearch.org/bulletin}
\def\AliusIssueSpan{}
\def\AliusIssueEditors{}
\def\AliusIssueTagline{exploring the diversity of consciousness}
\def\AliusIssueDateLine{}
\def\AliusIssueWebsite{aliusresearch.org}
\def\AliusCoverSubjects{}
\def\AliusCoverLogoAsset{assets/cover-parts/leaf-logo.png}
\def\AliusCoverFigureAsset{assets/cover-parts/figure.png}
\def\AliusCoverPlantAsset{assets/cover-parts/plant.png}
\def\AliusCoverLogoX{10mm}
\def\AliusCoverLogoY{10mm}
\def\AliusCoverLogoWidth{36mm}
\def\AliusCoverTitleX{58mm}
\def\AliusCoverTitleY{9mm}
\def\AliusCoverWordmarkLineOne{ALIUS}
\def\AliusCoverWordmarkLineTwo{BULLETIN}
\def\AliusCoverWordmarkLineOneSize{50}
\def\AliusCoverWordmarkLineOneLeading{44}
\def\AliusCoverWordmarkLineTwoSize{44}
\def\AliusCoverWordmarkLineTwoLeading{38}
\def\AliusCoverWordmarkGap{27mm}
\def\AliusCoverTaglineX{10mm}
\def\AliusCoverTaglineY{72mm}
\def\AliusCoverTaglineSize{17}
\def\AliusCoverTaglineLeading{18}
\def\AliusCoverEditorsX{105mm}
\def\AliusCoverEditorsY{89mm}
\def\AliusCoverEditorsSize{12.5}
\def\AliusCoverEditorsLeading{14}
\def\AliusCoverEditorsWidth{120mm}
\def\AliusCoverSubjectsX{18mm}
\def\AliusCoverSubjectsY{111mm}
\def\AliusCoverSubjectsWidth{70mm}
\def\AliusCoverSubjectsSize{15}
\def\AliusCoverSubjectsLeading{17}
\def\AliusCoverSubjectsGap{2.8mm}
\def\AliusCoverFigureX{74mm}
\def\AliusCoverFigureY{86mm}
\def\AliusCoverFigureWidth{132mm}
\def\AliusCoverPlantX{14mm}
\def\AliusCoverPlantY{218mm}
\def\AliusCoverPlantWidth{42mm}
\def\AliusCoverIssueNumberX{105mm}
\def\AliusCoverIssueNumberY{272mm}
\def\AliusCoverIssueNumberSize{22}
\def\AliusCoverIssueNumberLeading{22}
\def\AliusCoverDateX{105mm}
\def\AliusCoverDateY{283mm}
\def\AliusCoverDateSize{19}
\def\AliusCoverDateLeading{20}
\def\AliusCoverWebsiteX{105mm}
\def\AliusCoverWebsiteY{294mm}
\def\AliusCoverWebsiteSize{20}
\def\AliusCoverWebsiteLeading{20}
\def\AliusCoverPanelControl{52mm}
\def\AliusCoverPanelRise{31mm}
\def\AliusQuestionTextSize{12.4}
\def\AliusQuestionTextLeading{14.8}
\def\AliusBodyTextSize{14}
\def\AliusBodyTextLeading{16.4}
\def\AliusSectionHeadingSize{14}
\def\AliusSectionHeadingLeading{16}
\def\AliusReferenceTextSize{13}
\def\AliusReferenceTextLeading{15.2}
\def\AliusPullQuoteTextSize{15}
\def\AliusPullQuoteTextLeading{18}
\def\AliusPullQuoteMarkSize{48}
\def\AliusPullQuoteWidth{0.76\linewidth}

\newcommand{\AliusEnableBundleMode}{\AliusBundleModetrue}
\newcommand{\AliusDisableBundleMode}{\AliusBundleModefalse}

\newcommand{\AliusSetIssueNumber}[1]{\gdef\AliusIssueNumber{#1}}
\newcommand{\AliusSetYear}[1]{\gdef\AliusYear{#1}}
\newcommand{\AliusSetPieceSlug}[1]{\gdef\AliusPieceSlug{#1}}
\newcommand{\AliusSetPieceType}[1]{\gdef\AliusPieceType{#1}}
\newcommand{\AliusSetTitle}[1]{\gdef\AliusTitle{#1}}
\newcommand{\AliusSetSubtitle}[1]{\gdef\AliusSubtitle{#1}}
\newcommand{\AliusSetCreditLine}[1]{\gdef\AliusCreditLine{#1}}
\newcommand{\AliusSetRunningTitle}[1]{\gdef\AliusRunningTitle{#1}}
\newcommand{\AliusSetCitationLabel}[1]{\gdef\AliusCitationLabel{#1}}
\newcommand{\AliusSetStandaloneCitation}[1]{\gdef\AliusStandaloneCitation{#1}}
\newcommand{\AliusSetBundleCitation}[1]{\gdef\AliusBundleCitation{#1}}
\newcommand{\AliusSetAbstract}[1]{\gdef\AliusAbstract{#1}}
\newcommand{\AliusSetKeywordsLabel}[1]{\gdef\AliusKeywordsLabel{#1}}
\newcommand{\AliusSetKeywords}[1]{\gdef\AliusKeywords{#1}}
\newcommand{\AliusSetTitleSize}[2]{\gdef\AliusTitleSize{#1}\gdef\AliusTitleLeading{#2}}
\newcommand{\AliusSetSubtitleSize}[2]{\gdef\AliusSubtitleSize{#1}\gdef\AliusSubtitleLeading{#2}}
\newcommand{\AliusSetCreditSize}[2]{\gdef\AliusCreditSize{#1}\gdef\AliusCreditLeading{#2}}
\newcommand{\AliusSetFooterPrefix}[1]{\gdef\AliusFooterPrefix{#1}}
\newcommand{\AliusSetFooterUrl}[1]{\gdef\AliusFooterUrl{#1}}
\newcommand{\AliusSetIssueSpan}[1]{\gdef\AliusIssueSpan{#1}}
\newcommand{\AliusSetIssueEditors}[1]{\gdef\AliusIssueEditors{#1}}
\newcommand{\AliusSetIssueTagline}[1]{\gdef\AliusIssueTagline{#1}}
\newcommand{\AliusSetIssueDateLine}[1]{\gdef\AliusIssueDateLine{#1}}
\newcommand{\AliusSetIssueWebsite}[1]{\gdef\AliusIssueWebsite{#1}}
\newcommand{\AliusSetPrimaryGreen}[1]{\colorlet{AliusGreen}{#1}}
\newcommand{\AliusSetDarkGreen}[1]{\colorlet{AliusGreenDark}{#1}}
\newcommand{\AliusSetCoverInkColor}[1]{\colorlet{AliusCoverInk}{#1}}
\newcommand{\AliusSetCoverPanelColor}[1]{\colorlet{AliusCoverPanel}{#1}}
\newcommand{\AliusSetBodyColor}[1]{\colorlet{AliusBody}{#1}\color{AliusBody}}
\newcommand{\AliusSetCoverLogoAsset}[1]{\gdef\AliusCoverLogoAsset{#1}}
\newcommand{\AliusSetCoverFigureAsset}[1]{\gdef\AliusCoverFigureAsset{#1}}
\newcommand{\AliusSetCoverPlantAsset}[1]{\gdef\AliusCoverPlantAsset{#1}}
\newcommand{\AliusSetCoverLogoPosition}[2]{\gdef\AliusCoverLogoX{#1}\gdef\AliusCoverLogoY{#2}}
\newcommand{\AliusSetCoverLogoWidth}[1]{\gdef\AliusCoverLogoWidth{#1}}
\newcommand{\AliusSetCoverTitlePosition}[2]{\gdef\AliusCoverTitleX{#1}\gdef\AliusCoverTitleY{#2}}
\newcommand{\AliusSetCoverWordmarkLines}[2]{\gdef\AliusCoverWordmarkLineOne{#1}\gdef\AliusCoverWordmarkLineTwo{#2}}
\newcommand{\AliusSetCoverWordmarkSize}[4]{\gdef\AliusCoverWordmarkLineOneSize{#1}\gdef\AliusCoverWordmarkLineOneLeading{#2}\gdef\AliusCoverWordmarkLineTwoSize{#3}\gdef\AliusCoverWordmarkLineTwoLeading{#4}}
\newcommand{\AliusSetCoverWordmarkGap}[1]{\gdef\AliusCoverWordmarkGap{#1}}
\newcommand{\AliusSetCoverTaglinePosition}[2]{\gdef\AliusCoverTaglineX{#1}\gdef\AliusCoverTaglineY{#2}}
\newcommand{\AliusSetCoverTaglineSize}[2]{\gdef\AliusCoverTaglineSize{#1}\gdef\AliusCoverTaglineLeading{#2}}
\newcommand{\AliusSetCoverEditorsPosition}[2]{\gdef\AliusCoverEditorsX{#1}\gdef\AliusCoverEditorsY{#2}}
\newcommand{\AliusSetCoverEditorsSize}[2]{\gdef\AliusCoverEditorsSize{#1}\gdef\AliusCoverEditorsLeading{#2}}
\newcommand{\AliusSetCoverEditorsWidth}[1]{\gdef\AliusCoverEditorsWidth{#1}}
\newcommand{\AliusSetCoverSubjectsPosition}[2]{\gdef\AliusCoverSubjectsX{#1}\gdef\AliusCoverSubjectsY{#2}}
\newcommand{\AliusSetCoverSubjectsWidth}[1]{\gdef\AliusCoverSubjectsWidth{#1}}
\newcommand{\AliusSetCoverSubjectsSize}[2]{\gdef\AliusCoverSubjectsSize{#1}\gdef\AliusCoverSubjectsLeading{#2}}
\newcommand{\AliusSetCoverSubjectsGap}[1]{\gdef\AliusCoverSubjectsGap{#1}}
\newcommand{\AliusSetCoverFigurePosition}[2]{\gdef\AliusCoverFigureX{#1}\gdef\AliusCoverFigureY{#2}}
\newcommand{\AliusSetCoverFigureWidth}[1]{\gdef\AliusCoverFigureWidth{#1}}
\newcommand{\AliusSetCoverPlantPosition}[2]{\gdef\AliusCoverPlantX{#1}\gdef\AliusCoverPlantY{#2}}
\newcommand{\AliusSetCoverPlantWidth}[1]{\gdef\AliusCoverPlantWidth{#1}}
\newcommand{\AliusSetCoverIssueNumberPosition}[2]{\gdef\AliusCoverIssueNumberX{#1}\gdef\AliusCoverIssueNumberY{#2}}
\newcommand{\AliusSetCoverIssueNumberSize}[2]{\gdef\AliusCoverIssueNumberSize{#1}\gdef\AliusCoverIssueNumberLeading{#2}}
\newcommand{\AliusSetCoverDatePosition}[2]{\gdef\AliusCoverDateX{#1}\gdef\AliusCoverDateY{#2}}
\newcommand{\AliusSetCoverDateSize}[2]{\gdef\AliusCoverDateSize{#1}\gdef\AliusCoverDateLeading{#2}}
\newcommand{\AliusSetCoverWebsitePosition}[2]{\gdef\AliusCoverWebsiteX{#1}\gdef\AliusCoverWebsiteY{#2}}
\newcommand{\AliusSetCoverWebsiteSize}[2]{\gdef\AliusCoverWebsiteSize{#1}\gdef\AliusCoverWebsiteLeading{#2}}
\newcommand{\AliusSetCoverPanelCurve}[2]{\gdef\AliusCoverPanelControl{#1}\gdef\AliusCoverPanelRise{#2}}
\newcommand{\AliusSetQuestionTypography}[2]{\gdef\AliusQuestionTextSize{#1}\gdef\AliusQuestionTextLeading{#2}}
\newcommand{\AliusSetBodyTypography}[2]{\gdef\AliusBodyTextSize{#1}\gdef\AliusBodyTextLeading{#2}}
\newcommand{\AliusSetSectionHeadingTypography}[2]{\gdef\AliusSectionHeadingSize{#1}\gdef\AliusSectionHeadingLeading{#2}}
\newcommand{\AliusSetReferenceTypography}[2]{\gdef\AliusReferenceTextSize{#1}\gdef\AliusReferenceTextLeading{#2}}
\newcommand{\AliusSetPullQuoteTypography}[3]{\gdef\AliusPullQuoteTextSize{#1}\gdef\AliusPullQuoteTextLeading{#2}\gdef\AliusPullQuoteMarkSize{#3}}
\newcommand{\AliusSetPullQuoteWidth}[1]{\gdef\AliusPullQuoteWidth{#1}}
\newcommand{\AliusClearContributors}{\gdef\AliusContributors{}}
\newcommand{\AliusClearCoverSubjects}{\gdef\AliusCoverSubjects{}}
\newcommand{\AliusAddCoverSubject}[1]{%
  \gappto\AliusCoverSubjects{%
    {\AliusCormorantLight\fontsize{\AliusCoverSubjectsSize}{\AliusCoverSubjectsLeading}\selectfont #1\par}%
    \vspace{\AliusCoverSubjectsGap}%
  }%
}
\newcommand{\AliusAddContributor}[2]{%
  \gappto\AliusContributors{%
    {\AliusLato\fontsize{11}{13}\selectfont #1\par}%
    {\AliusLatoLight\fontsize{9}{11}\selectfont #2\par}%
    \vspace{0.9em}%
  }%
}

\newcommand{\AliusCurrentCitation}{%
  \ifAliusBundleMode
    \ifx\AliusBundleCitation\@empty
      \AliusStandaloneCitation
    \else
      \AliusBundleCitation
    \fi
  \else
    \AliusStandaloneCitation
  \fi
}

\newcommand{\AliusFooterText}{%
  \AliusFooterPrefix\ n\textdegree\ \AliusIssueNumber\ (\AliusYear)\hfill \AliusFooterUrl%
}

\newcommand{\AliusHeaderTitle}{%
  \ifx\AliusRunningTitle\@empty
    \AliusTitle
  \else
    \AliusRunningTitle
  \fi
}

\fancypagestyle{aliuspiece}{%
  \fancyhf{}%
  \fancyhead[C]{%
    \begin{tabular}{c}
      {\AliusCormorantLight\fontsize{14}{15}\selectfont \AliusHeaderTitle}\\[-1pt]
      {\AliusCormorantLight\fontsize{12}{12}\selectfont \thepage}
    \end{tabular}%
  }%
  \fancyfoot[C]{%
    {\AliusCormorantLight\fontsize{12}{12}\selectfont \AliusFooterText}%
  }%
  \renewcommand{\headrulewidth}{0pt}%
  \renewcommand{\footrulewidth}{0pt}%
}

\fancypagestyle{aliusfirstpage}{%
  \fancyhf{}%
  \fancyfoot[C]{%
    {\AliusCormorantLight\fontsize{12}{12}\selectfont \AliusFooterText}%
  }%
  \renewcommand{\headrulewidth}{0pt}%
  \renewcommand{\footrulewidth}{0pt}%
}

\pagestyle{aliuspiece}

\newcommand{\AliusRenderContributors}{%
  \begingroup
  \RaggedRight
  \AliusContributors
  \endgroup
}

\newcommand{\AliusRenderFrontMatter}{%
  \thispagestyle{aliusfirstpage}%
  {\AliusLato\fontsize{\AliusTitleSize}{\AliusTitleLeading}\selectfont \AliusTitle\par}%
  \ifx\AliusSubtitle\@empty\else
    \vspace{0.8em}%
    {\AliusLatoLight\fontsize{\AliusSubtitleSize}{\AliusSubtitleLeading}\selectfont \AliusSubtitle\par}%
  \fi
  \ifx\AliusCreditLine\@empty\else
    \vspace{1.1em}%
    {\AliusLatoLight\fontsize{\AliusCreditSize}{\AliusCreditLeading}\selectfont \AliusCreditLine\par}%
  \fi
  \vspace{1.1em}%
  \begin{minipage}[t]{0.64\textwidth}
    {\AliusLatoLight\fontsize{10}{12.5}\selectfont \AliusCitationLabel\ \AliusCurrentCitation\par}%
  \end{minipage}\hfill
  \begin{minipage}[t]{0.28\textwidth}
    \AliusRenderContributors
  \end{minipage}%
  \vspace{1.3em}%
  {\AliusLato\fontsize{14}{16}\selectfont Abstract\par}%
  \vspace{0.55em}%
  {\AliusLatoLight\fontsize{12}{15}\selectfont \AliusAbstract\par}%
  \ifx\AliusKeywords\@empty\else
    \vspace{1em}%
    {\AliusLatoLight\fontsize{12}{14}\selectfont \textit{\AliusKeywordsLabel}\ \textit{\AliusKeywords}\par}%
  \fi
  \vspace{1.3em}%
}

\newcommand{\AliusStartPiece}{%
  \clearpage
  \label{\AliusPieceSlug:start}%
  \AliusRenderFrontMatter
  \pagestyle{aliuspiece}%
}

\newcommand{\AliusStartPieceHere}{%
  \label{\AliusPieceSlug:start}%
  \AliusRenderFrontMatter
  \pagestyle{aliuspiece}%
}

\newcommand{\AliusFinishPiece}{%
  \par
  \label{\AliusPieceSlug:end}%
}

\NewDocumentCommand{\AliusQuestion}{m}{%
  \vspace{1.05em}%
  {\AliusLato\fontsize{\AliusQuestionTextSize}{\AliusQuestionTextLeading}\selectfont #1\par}%
}

\NewDocumentCommand{\AliusAnswer}{m}{%
  \vspace{0.72em}%
  {\fontsize{\AliusBodyTextSize}{\AliusBodyTextLeading}\selectfont #1\par}%
}

\NewDocumentCommand{\AliusSpeakerAnswer}{m m}{%
  \vspace{0.72em}%
  {\fontsize{\AliusBodyTextSize}{\AliusBodyTextLeading}\selectfont \textbf{#1}\ #2\par}%
}

\NewDocumentCommand{\AliusParagraph}{m}{%
  \vspace{0.72em}%
  {\fontsize{\AliusBodyTextSize}{\AliusBodyTextLeading}\selectfont #1\par}%
}

\NewDocumentCommand{\AliusSectionHeading}{m}{%
  \vspace{1.4em}%
  {\AliusLato\fontsize{\AliusSectionHeadingSize}{\AliusSectionHeadingLeading}\selectfont #1\par}%
  \vspace{0.4em}%
}

\NewDocumentCommand{\AliusReferenceEntry}{m}{%
  \vspace{0.35em}%
  {\fontsize{\AliusReferenceTextSize}{\AliusReferenceTextLeading}\selectfont \hangindent=1.4em \hangafter=1 #1\par}%
}

\NewDocumentCommand{\AliusPullQuote}{m}{%
  \vspace{1.25em}%
  \begin{center}
    \makebox[0pt][l]{\hspace*{-1.0em}{\AliusCormorantLight\fontsize{\AliusPullQuoteMarkSize}{36}\selectfont ``}}%
    \begin{minipage}{\AliusPullQuoteWidth}
      \centering
      {\AliusLatoLight\fontsize{\AliusPullQuoteTextSize}{\AliusPullQuoteTextLeading}\selectfont #1\par}%
    \end{minipage}%
    \makebox[0pt][r]{{\AliusCormorantLight\fontsize{\AliusPullQuoteMarkSize}{36}\selectfont ''}}%
  \end{center}
  \vspace{0.8em}%
}

\NewDocumentCommand{\AliusIssueCoverPage}{m}{%
  \clearpage
  \thispagestyle{empty}%
  \noindent\includegraphics[width=\paperwidth,height=\paperheight]{#1}%
  \clearpage
}

\newcommand{\AliusRenderIssueCover}{%
  \clearpage
  \thispagestyle{empty}%
  \begin{tikzpicture}[remember picture,overlay,x=1mm,y=1mm]
    \fill[AliusCoverPanel] ([yshift=0mm]current page.south west)
      .. controls ([xshift=\AliusCoverPanelControl,yshift=\AliusCoverPanelRise]current page.south west)
      and ([xshift=-\AliusCoverPanelControl,yshift=\AliusCoverPanelRise]current page.south east)
      .. ([yshift=0mm]current page.south east)
      -- (current page.south east)
      -- (current page.south west)
      -- cycle;
    \node[anchor=north west] at ([xshift=\AliusCoverLogoX,yshift=-\AliusCoverLogoY]current page.north west)
      {\includegraphics[width=\AliusCoverLogoWidth]{\AliusCoverLogoAsset}};
    \node[anchor=north west,text=AliusGreen] at ([xshift=\AliusCoverTitleX,yshift=-\AliusCoverTitleY]current page.north west)
      {{\AliusLatoLight\fontsize{\AliusCoverWordmarkLineOneSize}{\AliusCoverWordmarkLineOneLeading}\selectfont \AliusCoverWordmarkLineOne}};
    \node[anchor=north west,text=AliusGreen] at ([xshift=\AliusCoverTitleX,yshift=-\AliusCoverWordmarkGap-\AliusCoverTitleY]current page.north west)
      {{\AliusLatoLight\fontsize{\AliusCoverWordmarkLineTwoSize}{\AliusCoverWordmarkLineTwoLeading}\selectfont \AliusCoverWordmarkLineTwo}};
    \node[anchor=north west,text=AliusGreen] at ([xshift=\AliusCoverTaglineX,yshift=-\AliusCoverTaglineY]current page.north west)
      {{\AliusLatoLight\fontsize{\AliusCoverTaglineSize}{\AliusCoverTaglineLeading}\selectfont \AliusIssueTagline}};
    \node[anchor=north,text=AliusGreenDark,align=center,text width=\AliusCoverEditorsWidth] at ([xshift=\AliusCoverEditorsX,yshift=-\AliusCoverEditorsY]current page.north west)
      {{\AliusLatoLight\fontsize{\AliusCoverEditorsSize}{\AliusCoverEditorsLeading}\selectfont \AliusIssueEditors}};
    \node[anchor=north west,align=center,text=AliusCoverInk,text width=\AliusCoverSubjectsWidth] at ([xshift=\AliusCoverSubjectsX,yshift=-\AliusCoverSubjectsY]current page.north west)
      {\AliusCoverSubjects};
    \node[anchor=north west] at ([xshift=\AliusCoverFigureX,yshift=-\AliusCoverFigureY]current page.north west)
      {\includegraphics[width=\AliusCoverFigureWidth]{\AliusCoverFigureAsset}};
    \node[anchor=north west] at ([xshift=\AliusCoverPlantX,yshift=-\AliusCoverPlantY]current page.north west)
      {\includegraphics[width=\AliusCoverPlantWidth]{\AliusCoverPlantAsset}};
    \node[anchor=center,text=white] at ([xshift=\AliusCoverIssueNumberX,yshift=-\AliusCoverIssueNumberY]current page.north west)
      {{\AliusLatoLight\fontsize{\AliusCoverIssueNumberSize}{\AliusCoverIssueNumberLeading}\selectfont n\textdegree\AliusIssueNumber}};
    \node[anchor=center,text=white] at ([xshift=\AliusCoverDateX,yshift=-\AliusCoverDateY]current page.north west)
      {{\AliusLatoLight\fontsize{\AliusCoverDateSize}{\AliusCoverDateLeading}\selectfont \AliusIssueDateLine}};
    \node[anchor=center,text=AliusGreen] at ([xshift=\AliusCoverWebsiteX,yshift=-\AliusCoverWebsiteY]current page.north west)
      {{\AliusLatoLight\fontsize{\AliusCoverWebsiteSize}{\AliusCoverWebsiteLeading}\selectfont \AliusIssueWebsite}};
  \end{tikzpicture}%
  \null
  \clearpage
}

\NewDocumentCommand{\AliusIssueBlankPage}{}{%
  \clearpage
  \thispagestyle{empty}%
  \null
  \clearpage
}

\NewDocumentCommand{\AliusIssueCenteredTitle}{m}{%
  \clearpage
  \thispagestyle{empty}%
  \vspace*{2.4cm}%
  \begin{center}
    {\AliusLato\fontsize{22}{28}\selectfont #1\par}
  \end{center}
  \vspace{1.5cm}%
}

\NewDocumentCommand{\AliusIssueTOCEntry}{m m m m}{%
  {\AliusLatoLight\fontsize{12}{15}\selectfont \textbf{#2}\ #3\par}%
  {\AliusLatoLight\fontsize{12}{15}\selectfont #4\dotfill \pageref*{#1:start}\par}%
  \vspace{0.9em}%
}

\makeatother
